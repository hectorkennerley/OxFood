from collections import defaultdict
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.db import HOME_COLLEGE_ID, get_session
from app.models import Claim, InventoryLot, Product, Recipe, Service, SupplierIssue, SurplusListing, WasteEvent
from app.seed import GO_LIVE_DAYS_AGO
from app.services.forecast import forecast_service

router = APIRouter(prefix="/api/analytics")

RECOVERED = {"offer_students", "chill_reuse", "marketplace", "donate", "staff_meal"}
STAGE_LABEL = {"prep_trim": "Prep trim", "overproduction": "Overproduction", "servery_leftover": "Servery leftover",
               "plate_waste": "Plate waste", "spoilage": "Spoilage", "cooking_error": "Cooking error"}


def _window(events, svc_map, start: date, end: date):
    return [w for w in events if start <= w.logged_at.date() <= end]


@router.get("/dashboard")
def dashboard(college_id: int = HOME_COLLEGE_ID, session: Session = Depends(get_session)):
    today = date.today()
    events = session.exec(select(WasteEvent).where(WasteEvent.college_id == college_id,
                                                   WasteEvent.logged_at >= datetime.combine(today - timedelta(days=60), datetime.min.time()))).all()
    services = session.exec(select(Service).where(Service.college_id == college_id, Service.date <= today)).all()
    svc_map = {s.id: s for s in services}
    recipes = {r.id: r for r in session.exec(select(Recipe)).all()}

    def covers(start, end):
        return sum(s.attended for s in services if start <= s.date <= end)

    def kpis(start, end):
        ev = _window(events, svc_map, start, end)
        kg = sum(w.weight_kg for w in ev)
        cooked_waste = [w for w in ev if w.stage in ("overproduction", "servery_leftover")]
        rec_kg = sum(w.weight_kg for w in cooked_waste if w.disposition in RECOVERED)
        cv = covers(start, end)
        return {"kg": round(kg, 1), "gbp": round(sum(w.value_gbp for w in ev), 2),
                "g_per_cover": round(kg * 1000 / cv) if cv else 0, "covers": cv,
                "pct_recovered": round(100 * rec_kg / sum(w.weight_kg for w in cooked_waste)) if cooked_waste else 0,
                "gbp_rescued": round(sum(w.value_gbp for w in ev if w.disposition in RECOVERED), 2),
                "co2e_kg": round(kg * 2.5)}  # placeholder factor; replace with a sourced value

    this_wk = kpis(today - timedelta(days=6), today)
    last_wk = kpis(today - timedelta(days=13), today - timedelta(days=7))

    # Income from surplus (student meal sales + stock sold to other colleges), last 7 days
    my_listings = {l.id: l for l in session.exec(select(SurplusListing).where(SurplusListing.college_id == college_id)).all()}
    claims = session.exec(select(Claim).where(Claim.created_at >= datetime.combine(today - timedelta(days=6), datetime.min.time()))).all()
    sales = [c for c in claims if c.listing_id in my_listings]
    this_wk["gbp_sales"] = round(sum(c.amount_gbp for c in sales), 2)
    this_wk["meals_claimed"] = int(sum(c.qty for c in sales if my_listings[c.listing_id].kind == "meal_to_students"))

    week = _window(events, svc_map, today - timedelta(days=6), today)
    by_stage = defaultdict(float)
    by_dish = defaultdict(float)
    by_meal = defaultdict(float)
    by_hour = defaultdict(float)
    for w in week:
        by_stage[w.stage] += w.weight_kg
        name = recipes[w.recipe_id].name if w.recipe_id else None
        if name and w.stage in ("overproduction", "servery_leftover", "cooking_error"):
            by_dish[name] += w.weight_kg
        if w.service_id in svc_map:
            by_meal[svc_map[w.service_id].meal] += w.weight_kg
        by_hour[w.logged_at.hour] += w.weight_kg

    # 8-week trend
    trend = []
    for k in range(7, -1, -1):
        end = today - timedelta(days=7 * k)
        start = end - timedelta(days=6)
        ev = _window(events, svc_map, start, end)
        kg = sum(w.weight_kg for w in ev)
        cv = covers(start, end)
        trend.append({"week": start.strftime("%d %b"), "kg": round(kg), "g_per_cover": round(kg * 1000 / cv) if cv else 0,
                      "live": (today - start).days <= GO_LIVE_DAYS_AGO})

    # Sankey: where last week's food went (kg)
    wk_svcs = [s for s in services if today - timedelta(days=6) <= s.date <= today and s.attended]
    cooked = sum(s.planned_portions * 0.42 for s in wk_svcs)
    over = by_stage["overproduction"]
    serv = by_stage["servery_leftover"]
    plate = by_stage["plate_waste"]
    trim = by_stage["prep_trim"]
    spoil = by_stage["spoilage"] + by_stage["cooking_error"]
    rec = defaultdict(float)
    for w in week:
        if w.stage in ("overproduction", "servery_leftover"):
            rec[(w.stage, w.disposition in RECOVERED)] += w.weight_kg
    served = max(cooked - over, 0)
    eaten = max(served - serv - plate, 0)
    nodes = ["Purchased", "Cooked", "Prep trim", "Spoiled", "Served", "Overproduction", "Eaten", "Servery leftover",
             "Plate waste", "Recovered", "Binned / compost"]
    links = [(0, 1, cooked), (0, 2, trim), (0, 3, spoil), (1, 4, served), (1, 5, over), (4, 6, eaten), (4, 7, serv),
             (4, 8, plate), (5, 9, rec[("overproduction", True)]), (5, 10, rec[("overproduction", False)]),
             (7, 9, rec[("servery_leftover", True)]), (7, 10, rec[("servery_leftover", False)])]
    sankey = {"nodes": [{"name": n} for n in nodes],
              "links": [{"source": a, "target": b, "value": round(v, 1)} for a, b, v in links if v > 0.05]}

    # Alerts
    expiring = session.exec(select(InventoryLot, Product).join(Product).where(
        InventoryLot.college_id == college_id, InventoryLot.status == "in_stock",
        InventoryLot.expiry_date <= today + timedelta(days=2))).all()
    open_issues = session.exec(select(SupplierIssue).where(SupplierIssue.college_id == college_id,
                                                           SupplierIssue.resolved == False)).all()  # noqa: E712
    tonight = session.exec(select(Service).where(Service.college_id == college_id, Service.date == today,
                                                 Service.meal == "dinner")).first()
    alerts = []
    for lot, p in sorted(expiring, key=lambda x: x[0].expiry_date):
        d = (lot.expiry_date - today).days
        alerts.append({"level": "red" if d <= 0 else "amber", "kind": "expiry", "lot_id": lot.id,
                       "text": f"{p.name}: {lot.qty:g} pack(s) {'expire today' if d <= 0 else f'expire in {d} day(s)'} "
                               f"(£{lot.qty * p.price:.0f})"})
    for i in open_issues:
        p = session.get(Product, i.product_id) if i.product_id else None
        alerts.append({"level": "amber", "kind": "supplier", "text": f"Open supplier issue: {i.notes}" + (f" ({p.name})" if p else "")})

    return {"this_week": this_wk, "last_week": last_wk,
            "by_stage": [{"stage": STAGE_LABEL.get(k, k), "kg": round(v, 1)} for k, v in sorted(by_stage.items(), key=lambda x: -x[1])],
            "top_dishes": [{"dish": k, "kg": round(v, 1)} for k, v in sorted(by_dish.items(), key=lambda x: -x[1])[:8]],
            "by_meal": [{"meal": m, "kg": round(by_meal.get(m, 0), 1)} for m in ("breakfast", "lunch", "dinner")],
            "by_hour": [{"hour": f"{h:02d}:00", "kg": round(by_hour.get(h, 0), 1)} for h in range(6, 23)],
            "trend": trend, "sankey": sankey, "alerts": alerts,
            "tonight": forecast_service(session, tonight) if tonight else None}
