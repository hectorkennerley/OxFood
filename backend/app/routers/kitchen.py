import random
from dataclasses import asdict
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.db import HOME_COLLEGE_ID, get_session
from app.models import Appliance, Claim, Notification, Recipe, Service, SurplusListing, WasteEvent
from app.routers.core import services_on
from app.services import ai
from app.services.recovery import KITCHEN_RECOVERY
from app.services.safety_rules import ReuseInput, advise

router = APIRouter(prefix="/api")


class WasteIn(BaseModel):
    college_id: int = HOME_COLLEGE_ID
    service_id: Optional[int] = None
    recipe_id: Optional[int] = None
    stage: str
    weight_kg: Optional[float] = None
    portions: Optional[int] = None
    method: str = "tablet"
    note: str = ""
    minutes_since_cooked: int = 30
    hot_held_63: bool = True


def _offer_price(r: Recipe) -> float:
    return max(1.0, round(r.sell_price * 0.5 * 2) / 2)


@router.post("/waste")
def log_waste(body: WasteIn, session: Session = Depends(get_session)):
    r = session.get(Recipe, body.recipe_id) if body.recipe_id else None
    weight, portions = body.weight_kg, body.portions
    if r and weight is None and portions:
        weight = round(portions * r.portion_g / 1000, 2)
    if r and portions is None and weight:
        portions = int(weight * 1000 / r.portion_g)
    if weight is None:
        raise HTTPException(400, "Give a weight or a number of portions")
    value = round((portions or 0) * r.cost_per_portion, 2) if r else round(weight * 3.0, 2)
    ev = WasteEvent(college_id=body.college_id, service_id=body.service_id, recipe_id=body.recipe_id, stage=body.stage,
                    weight_kg=weight, portions_est=portions or 0, value_gbp=value, logged_at=datetime.now(),
                    method=body.method, note=body.note, disposition="pending")
    session.add(ev)
    session.commit()
    session.refresh(ev)
    chiller = session.exec(select(Appliance).where(Appliance.college_id == body.college_id,
                                                   Appliance.type == "blast_chiller")).first() is not None
    adv = advise(ReuseInput(stage=body.stage, high_risk=bool(r and r.high_risk), blast_chiller=chiller,
                            minutes_since_cooked=body.minutes_since_cooked, hot_held_63=body.hot_held_63,
                            within_service_window=body.stage in ("overproduction", "servery_leftover")))
    return {"event": ev.model_dump(), "advice": asdict(adv), "tip": KITCHEN_RECOVERY.get(body.stage),
            "offer": {"portions": portions or 0, "suggested_price": _offer_price(r) if r else 0,
                      "normal_price": r.sell_price if r else 0, "dish": r.name if r else None}}


class DispositionIn(BaseModel):
    disposition: str


@router.post("/waste/{event_id}/disposition")
def set_disposition(event_id: int, body: DispositionIn, session: Session = Depends(get_session)):
    ev = session.get(WasteEvent, event_id)
    if not ev:
        raise HTTPException(404)
    ev.disposition = body.disposition
    session.add(ev)
    session.commit()
    return ev.model_dump()


@router.get("/waste/recent")
def recent_waste(college_id: int = HOME_COLLEGE_ID, session: Session = Depends(get_session)):
    rows = session.exec(select(WasteEvent).where(WasteEvent.college_id == college_id, WasteEvent.method != "seed")
                        .order_by(WasteEvent.logged_at.desc()).limit(15)).all()
    out = []
    for w in rows:
        r = session.get(Recipe, w.recipe_id) if w.recipe_id else None
        out.append({**w.model_dump(), "dish": r.name if r else None, "emoji": r.emoji if r else "🗑️"})
    return out


# ------------------------------------------------------------------ AI
def _dishes(session: Session, service_id: Optional[int], college_id: int) -> list[dict]:
    if service_id:
        svc = session.get(Service, service_id)
        return [{"id": rid, "name": session.get(Recipe, rid).name} for rid in svc.recipe_ids]
    out = []
    for svc in services_on(session, college_id, datetime.now().date()):
        out += [{"id": d["id"], "name": d["name"]} for d in svc["dishes"]]
    return out


class ParseIn(BaseModel):
    transcript: str
    college_id: int = HOME_COLLEGE_ID
    service_id: Optional[int] = None


@router.post("/ai/parse-waste")
def parse_waste(body: ParseIn, session: Session = Depends(get_session)):
    return ai.parse_waste(session, body.transcript, _dishes(session, body.service_id, body.college_id))


class PhotoIn(BaseModel):
    image_b64: str
    media_type: str = "image/jpeg"
    college_id: int = HOME_COLLEGE_ID
    service_id: Optional[int] = None


@router.post("/ai/classify-photo")
def classify_photo(body: PhotoIn, session: Session = Depends(get_session)):
    if len(body.image_b64) > 2_000_000:
        raise HTTPException(413, "Image too large: downscale it first")
    return ai.classify_photo(session, body.image_b64, body.media_type, _dishes(session, body.service_id, body.college_id))


@router.get("/ai/status")
def ai_status(session: Session = Depends(get_session)):
    return ai.ai_status(session)


# ------------------------------------------------------------------ Student offers
class OfferIn(BaseModel):
    waste_event_id: int
    portions: int
    price: float
    location: str = "Hall servery"
    minutes: int = 90


@router.post("/listings/offer")
def offer_to_students(body: OfferIn, session: Session = Depends(get_session)):
    ev = session.get(WasteEvent, body.waste_event_id)
    if not ev:
        raise HTTPException(404)
    r = session.get(Recipe, ev.recipe_id) if ev.recipe_id else None
    now = datetime.now()
    until = now + timedelta(minutes=body.minutes)
    name = r.name if r else "Surplus food"
    lst = SurplusListing(college_id=ev.college_id, kind="meal_to_students", recipe_id=ev.recipe_id, waste_event_id=ev.id,
                         title=name, qty=body.portions, qty_remaining=body.portions, price=body.price,
                         location=body.location, created_at=now, available_until=until)
    session.add(lst)
    ev.disposition = "offer_students"
    session.add(ev)
    session.flush()
    free = body.price == 0
    title = "🆓 Free food alert" if free else f"🍽️ {body.portions} portions available"
    body_txt = (f"{body.portions} portions of {name.lower()}, {'free' if free else f'£{body.price:.2f}'}, "
                f"{body.location} until {until.strftime('%H:%M')}. First come, first served.")
    session.add(Notification(college_id=ev.college_id, title=title, body=body_txt, listing_id=lst.id, created_at=now))
    session.commit()
    session.refresh(lst)
    return lst.model_dump()


@router.get("/student/feed")
def student_feed(college_id: int = HOME_COLLEGE_ID, session: Session = Depends(get_session)):
    now = datetime.now()
    listings = session.exec(select(SurplusListing).where(SurplusListing.college_id == college_id,
                                                         SurplusListing.kind == "meal_to_students",
                                                         SurplusListing.status == "open",
                                                         SurplusListing.available_until > now)
                            .order_by(SurplusListing.created_at.desc())).all()
    out = []
    for l in listings:
        r = session.get(Recipe, l.recipe_id) if l.recipe_id else None
        out.append({**l.model_dump(), "emoji": r.emoji if r else "🍽️", "allergens": r.allergens if r else [],
                    "normal_price": r.sell_price if r else None})
    notes = session.exec(select(Notification).where(Notification.college_id == college_id)
                         .order_by(Notification.created_at.desc()).limit(10)).all()
    return {"listings": out, "notifications": [n.model_dump() for n in notes]}


class ClaimIn(BaseModel):
    qty: float = 1
    student_pseudo_id: Optional[str] = None
    buyer_college_id: Optional[int] = None


@router.post("/listings/{listing_id}/claim")
def claim(listing_id: int, body: ClaimIn, session: Session = Depends(get_session)):
    lst = session.get(SurplusListing, listing_id)
    if not lst or lst.status != "open":
        raise HTTPException(404, "Listing no longer available")
    if body.qty > lst.qty_remaining:
        raise HTTPException(409, f"Only {lst.qty_remaining:g} left")
    lst.qty_remaining -= body.qty
    if lst.qty_remaining <= 0:
        lst.status = "sold_out"
    c = Claim(listing_id=lst.id, buyer_college_id=body.buyer_college_id,
              student_pseudo_id=body.student_pseudo_id or f"S-DEMO{random.randint(100, 999)}", qty=body.qty,
              amount_gbp=round(body.qty * lst.price, 2), pickup_code=f"{random.randint(100, 999)}",
              created_at=datetime.now())
    session.add(lst)
    session.add(c)
    session.commit()
    session.refresh(c)
    return {"claim": c.model_dump(), "listing": lst.model_dump()}
