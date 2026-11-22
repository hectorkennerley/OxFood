from collections import Counter, defaultdict
from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.db import HOME_COLLEGE_ID, get_session
from app.models import Appliance, Attendance, College, InventoryLot, Product, Recipe, RecipeIngredient, Service, WasteEvent
from app.services import ai
from app.services.forecast import forecast_service

router = APIRouter(prefix="/api")


def recipe_dict(r: Recipe) -> dict:
    return r.model_dump()


def services_on(session: Session, college_id: int, d: date) -> list[dict]:
    rows = session.exec(select(Service).where(Service.college_id == college_id, Service.date == d)).all()
    order = {"breakfast": 0, "lunch": 1, "dinner": 2}
    out = []
    for svc in sorted(rows, key=lambda s: order[s.meal]):
        dishes = [recipe_dict(session.get(Recipe, rid)) for rid in svc.recipe_ids]
        out.append({**svc.model_dump(), "dishes": dishes})
    return out


@router.get("/context")
def context(session: Session = Depends(get_session)):
    colleges = session.exec(select(College)).all()
    return {"today": date.today().isoformat(), "home_college_id": HOME_COLLEGE_ID,
            "colleges": [c.model_dump() for c in colleges], "ai": ai.ai_status(session)}


@router.post("/admin/reset")
def reset():
    from app.seed import seed

    seed()
    return {"ok": True}


@router.get("/services/today")
def services_today(college_id: int = HOME_COLLEGE_ID, session: Session = Depends(get_session)):
    return services_on(session, college_id, date.today())


@router.get("/recipes")
def recipes(session: Session = Depends(get_session)):
    out = []
    for r in session.exec(select(Recipe)).all():
        ings = session.exec(select(RecipeIngredient, Product).join(Product).where(RecipeIngredient.recipe_id == r.id)).all()
        out.append({**recipe_dict(r), "ingredients": [
            {"product_id": p.id, "name": p.name, "qty_per_portion": i.qty_per_portion, "unit": p.unit} for i, p in ings]})
    return out


@router.get("/forecast")
def forecast(college_id: int = HOME_COLLEGE_ID, session: Session = Depends(get_session)):
    today = date.today()
    upcoming = session.exec(select(Service).where(Service.college_id == college_id, Service.date >= today,
                                                  Service.date <= today + timedelta(days=6))).all()
    order = {"breakfast": 0, "lunch": 1, "dinner": 2}
    upcoming.sort(key=lambda s: (s.date, order[s.meal]))
    fc = [forecast_service(session, s) for s in upcoming if s.date > today or s.meal == "dinner"]

    past = session.exec(select(Service).where(Service.college_id == college_id, Service.date < today,
                                              Service.date >= today - timedelta(days=42), Service.booked > 0)).all()
    by = defaultdict(lambda: [0, 0])
    for s in past:
        key = (s.date.strftime("%a"), s.meal)
        by[key][0] += s.booked
        by[key][1] += s.attended
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    heat = [{"day": d, **{m: round(by[(d, m)][1] / by[(d, m)][0], 3) if by[(d, m)][0] else None
                          for m in ("breakfast", "lunch", "dinner")}} for d in days]
    ev = defaultdict(lambda: [0, 0])
    for s in past:
        ev[s.event_type][0] += s.booked
        ev[s.event_type][1] += s.attended
    events = [{"event_type": k, "show_rate": round(v[1] / v[0], 3)} for k, v in ev.items() if v[0]]

    recent = [s for s in past if s.date >= today - timedelta(days=14)]
    recent.sort(key=lambda s: (s.date, order[s.meal]))
    history = [{"label": f"{s.date.strftime('%a %d')} {s.meal[0].upper()}", "booked": s.booked, "attended": s.attended,
                "planned": s.planned_portions, "staff": s.staff_on_shift, "event_type": s.event_type} for s in recent]

    # Attendance habits (pseudonymised, home college only)
    att = session.exec(select(Attendance)).all()
    per_student = defaultdict(lambda: [0, 0])
    for a in att:
        per_student[a.student_id][0] += 1
        per_student[a.student_id][1] += a.scanned
    buckets = Counter()
    for b, sc in per_student.values():
        rate = sc / b if b else 0
        buckets[min(9, int(rate * 10))] += 1
    habits = [{"bucket": f"{i * 10}–{i * 10 + 9}%", "students": buckets.get(i, 0)} for i in range(10)]
    no_shows = sum(b - sc for b, sc in per_student.values())
    return {"upcoming": fc, "show_heatmap": heat, "by_event": events, "history": history, "habits": habits,
            "students_tracked": len(per_student), "no_show_meals_28d": no_shows}


@router.get("/menu/suggestions")
def menu_suggestions(meal: str = "lunch", college_id: int = HOME_COLLEGE_ID, use_ai: bool = False,
                     session: Session = Depends(get_session)):
    """Rank tomorrow's dishes by how much near-expiry stock and chillable leftovers they use up."""
    tomorrow = date.today() + timedelta(days=1)
    lots = session.exec(select(InventoryLot, Product).join(Product).where(
        InventoryLot.college_id == college_id, InventoryLot.status == "in_stock",
        InventoryLot.expiry_date <= tomorrow + timedelta(days=1))).all()
    expiring = {p.id: (lot, p) for lot, p in lots}
    chilled_today = session.exec(select(WasteEvent).where(
        WasteEvent.college_id == college_id, WasteEvent.disposition == "chill_reuse",
        WasteEvent.logged_at >= date.today().isoformat())).all()
    chilled_recipes = Counter(w.recipe_id for w in chilled_today)
    appliances = {a.type for a in session.exec(select(Appliance).where(Appliance.college_id == college_id)).all()}
    svc = session.exec(select(Service).where(Service.college_id == college_id, Service.date == tomorrow,
                                             Service.meal == meal)).first()
    staff = svc.staff_on_shift if svc else None

    pool = ["breakfast"] if meal == "breakfast" else ["lunch", "dinner"]
    cands = []
    for r in session.exec(select(Recipe).where(Recipe.meal_type.in_(pool))).all():
        ings = session.exec(select(RecipeIngredient).where(RecipeIngredient.recipe_id == r.id)).all()
        uses = []
        score = 0.0
        for i in ings:
            if i.product_id in expiring:
                lot, p = expiring[i.product_id]
                days = (lot.expiry_date - date.today()).days
                uses.append(f"{p.name} (expires {'today' if days <= 0 else f'in {days}d'})")
                score += 3 - max(0, days)
        reasons = []
        if r.id in chilled_recipes:
            score += 4
            reasons.append("Uses today's blast-chilled leftovers")
        missing = [a for a in r.appliances if a not in appliances]
        if missing:
            score -= 5
            reasons.append(f"Needs {', '.join(missing)} (not in this kitchen)")
        margin = r.sell_price - r.cost_per_portion
        score += margin / 4
        if staff and staff < 6 and len(r.stages) >= 4:
            score -= 0.5
            reasons.append("Fewer staff on shift: prefer a simpler dish")
        cands.append({"recipe_id": r.id, "name": r.name, "emoji": r.emoji, "score": round(score, 2), "uses_expiring": uses,
                      "reasons": reasons, "cost_per_portion": r.cost_per_portion, "sell_price": r.sell_price,
                      "margin": round(margin, 2)})
    cands.sort(key=lambda c: -c["score"])
    top = cands[:5]
    result = {"meal": meal, "date": tomorrow.isoformat(), "staff_on_shift": staff,
              "forecast": forecast_service(session, svc) if svc else None, "candidates": top, "ai": None}
    if use_ai:
        ctx = {"meal": meal, "forecast_covers": result["forecast"]["recommended_portions"] if svc else None,
               "candidates": [{k: c[k] for k in ("recipe_id", "name", "uses_expiring", "reasons", "sell_price", "cost_per_portion")} for c in top]}
        data, source = ai.menu_rationale(session, ctx)
        result["ai"] = {"source": source, **(data or {})}
    return result
