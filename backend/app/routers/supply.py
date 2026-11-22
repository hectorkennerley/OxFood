import random
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from sqlmodel import Session, select

from app.db import HOME_COLLEGE_ID, get_session
from app.models import (
    Claim, College, CollegeSupplier, InventoryLot, Order, OrderLine, Product, Recipe, RecipeIngredient, Service,
    StorageUnit, Supplier, SupplierIssue, SurplusListing, WasteEvent,
)
from app.services.foodbuy_csv import order_to_csv
from app.services.ordering import suggested_order
from app.services.recovery import SUPPLIER_RECOVERY
from app.services.storage import STORAGE_FOR, fit_check, unit_usage

router = APIRouter(prefix="/api")


# ------------------------------------------------------------------ Catalogue & suppliers
def _active_ids(session: Session, college_id: int) -> dict[int, bool]:
    return {cs.supplier_id: cs.active for cs in
            session.exec(select(CollegeSupplier).where(CollegeSupplier.college_id == college_id)).all()}


@router.get("/catalogue")
def catalogue(college_id: int = HOME_COLLEGE_ID, session: Session = Depends(get_session)):
    active = _active_ids(session, college_id)
    sups = {s.id: s for s in session.exec(select(Supplier)).all()}
    out = []
    for p in session.exec(select(Product)).all():
        if not active.get(p.supplier_id):
            continue
        out.append({**p.model_dump(), "supplier": sups[p.supplier_id].name, "supplier_code": sups[p.supplier_id].code,
                    "unit_price": round(p.price / p.pack_size, 2)})
    return out


@router.get("/suppliers")
def suppliers(college_id: int = HOME_COLLEGE_ID, session: Session = Depends(get_session)):
    active = _active_ids(session, college_id)
    issues = session.exec(select(SupplierIssue).where(SupplierIssue.college_id == college_id)).all()
    deliveries = Counter()
    for o in session.exec(select(Order).where(Order.college_id == college_id)).all():
        for sid in {session.get(Product, l.product_id).supplier_id for l in
                    session.exec(select(OrderLine).where(OrderLine.order_id == o.id)).all()}:
            deliveries[sid] += 1
    out = []
    for s in session.exec(select(Supplier)).all():
        mine = [i for i in issues if i.supplier_id == s.id]
        n_deliv = max(deliveries[s.id], 1) + 20  # include the 8-week delivery history (≈ 20 drops per supplier)
        rate = len(mine) / n_deliv
        out.append({**s.model_dump(), "active": active.get(s.id, False), "issues": len(mine),
                    "open_issues": sum(1 for i in mine if not i.resolved),
                    "issue_types": dict(Counter(i.type for i in mine).most_common()),
                    "reliability": round(100 * (1 - rate)),
                    "products": len(session.exec(select(Product).where(Product.supplier_id == s.id)).all())})
    out.sort(key=lambda s: s["reliability"])
    return out


class ToggleIn(BaseModel):
    college_id: int = HOME_COLLEGE_ID
    active: bool


@router.post("/suppliers/{supplier_id}/toggle")
def toggle_supplier(supplier_id: int, body: ToggleIn, session: Session = Depends(get_session)):
    cs = session.exec(select(CollegeSupplier).where(CollegeSupplier.college_id == body.college_id,
                                                    CollegeSupplier.supplier_id == supplier_id)).first()
    if not cs:
        cs = CollegeSupplier(college_id=body.college_id, supplier_id=supplier_id)
    cs.active = body.active
    session.add(cs)
    session.commit()
    return {"ok": True}


class SupplierIn(BaseModel):
    name: str
    category: str
    code: str
    lead_time_days: int = 1
    college_id: int = HOME_COLLEGE_ID


@router.post("/suppliers")
def add_supplier(body: SupplierIn, session: Session = Depends(get_session)):
    s = Supplier(code=body.code.upper(), name=body.name, category=body.category, lead_time_days=body.lead_time_days)
    session.add(s)
    session.flush()
    session.add(CollegeSupplier(college_id=body.college_id, supplier_id=s.id, active=True))
    session.commit()
    session.refresh(s)
    return s.model_dump()


@router.get("/suppliers/issues")
def supplier_issues(college_id: int = HOME_COLLEGE_ID, session: Session = Depends(get_session)):
    rows = session.exec(select(SupplierIssue).where(SupplierIssue.college_id == college_id)
                        .order_by(SupplierIssue.date.desc())).all()
    out = []
    for i in rows:
        p = session.get(Product, i.product_id) if i.product_id else None
        sub = session.get(Product, i.substitute_product_id) if i.substitute_product_id else None
        out.append({**i.model_dump(), "supplier": session.get(Supplier, i.supplier_id).name,
                    "product": p.name if p else None, "substitute": sub.name if sub else None,
                    "recovery": SUPPLIER_RECOVERY.get(i.type, [])})
    return out


class IssueIn(BaseModel):
    college_id: int = HOME_COLLEGE_ID
    supplier_id: int
    type: str
    product_id: Optional[int] = None
    substitute_product_id: Optional[int] = None
    notes: str = ""


@router.post("/suppliers/issues")
def add_issue(body: IssueIn, session: Session = Depends(get_session)):
    i = SupplierIssue(**body.model_dump(), date=date.today())
    session.add(i)
    session.commit()
    session.refresh(i)
    return {**i.model_dump(), "recovery": SUPPLIER_RECOVERY.get(i.type, [])}


@router.post("/suppliers/issues/{issue_id}/resolve")
def resolve_issue(issue_id: int, session: Session = Depends(get_session)):
    i = session.get(SupplierIssue, issue_id)
    i.resolved = True
    session.add(i)
    session.commit()
    return {"ok": True}


# ------------------------------------------------------------------ Orders
@router.get("/orders/suggested")
def get_suggested(college_id: int = HOME_COLLEGE_ID, days: int = 3, session: Session = Depends(get_session)):
    return suggested_order(session, college_id, days)


class LineIn(BaseModel):
    product_id: int
    qty: int


class OrderIn(BaseModel):
    college_id: int = HOME_COLLEGE_ID
    delivery_date: Optional[date] = None
    lines: list[LineIn]


@router.post("/orders")
def place_order(body: OrderIn, session: Session = Depends(get_session)):
    if not body.lines:
        raise HTTPException(400, "Empty order")
    o = Order(college_id=body.college_id, created_at=datetime.now(),
              delivery_date=body.delivery_date or date.today() + timedelta(days=1))
    session.add(o)
    session.flush()
    total = 0.0
    for l in body.lines:
        p = session.get(Product, l.product_id)
        session.add(OrderLine(order_id=o.id, product_id=p.id, qty=l.qty, unit_price=p.price))
        total += l.qty * p.price
    o.total = round(total, 2)
    o.exported_at = datetime.now()
    session.commit()
    session.refresh(o)
    return o.model_dump()


@router.get("/orders")
def list_orders(college_id: int = HOME_COLLEGE_ID, session: Session = Depends(get_session)):
    rows = session.exec(select(Order).where(Order.college_id == college_id).order_by(Order.created_at.desc()).limit(20)).all()
    return [{**o.model_dump(), "lines": len(session.exec(select(OrderLine).where(OrderLine.order_id == o.id)).all())} for o in rows]


@router.get("/orders/{order_id}/foodbuy.csv")
def foodbuy_csv(order_id: int, session: Session = Depends(get_session)):
    o = session.get(Order, order_id)
    if not o:
        raise HTTPException(404)
    col = session.get(College, o.college_id)
    lines = []
    for l in session.exec(select(OrderLine).where(OrderLine.order_id == o.id)).all():
        p = session.get(Product, l.product_id)
        s = session.get(Supplier, p.supplier_id)
        lines.append({"supplier_code": s.code, "supplier_name": s.name, "sku": p.sku, "name": p.name,
                      "pack_size": p.pack_size, "unit": p.unit, "qty": l.qty, "unit_price": l.unit_price})
    ref = f"OXF-{o.id:05d}"
    csv_text = order_to_csv(ref, col.name, col.cost_centre, o.delivery_date.isoformat(), lines)
    return Response(csv_text, media_type="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="{ref}-foodbuy.csv"'})


# ------------------------------------------------------------------ Inventory & storage
@router.get("/inventory")
def inventory(college_id: int = HOME_COLLEGE_ID, session: Session = Depends(get_session)):
    today = date.today()
    rows = session.exec(select(InventoryLot, Product).join(Product).where(
        InventoryLot.college_id == college_id, InventoryLot.status.in_(["in_stock", "listed"]))).all()
    units = {u.id: u.name for u in session.exec(select(StorageUnit).where(StorageUnit.college_id == college_id)).all()}
    lots = []
    for lot, p in rows:
        days = (lot.expiry_date - today).days
        lots.append({**lot.model_dump(), "product": p.name, "unit": p.unit, "pack_size": p.pack_size, "price": p.price,
                     "storage_type": p.storage_type, "hazard_class": p.hazard_class, "freezable": p.freezable,
                     "storage_unit": units.get(lot.storage_unit_id), "days_to_expiry": days,
                     "value_gbp": round(lot.qty * p.price, 2)})
    lots.sort(key=lambda l: l["days_to_expiry"])
    return {"lots": lots, "storage": unit_usage(session, college_id)}


class ListIn(BaseModel):
    price: float
    qty: Optional[float] = None


@router.post("/inventory/{lot_id}/list")
def list_lot(lot_id: int, body: ListIn, session: Session = Depends(get_session)):
    lot = session.get(InventoryLot, lot_id)
    p = session.get(Product, lot.product_id)
    col = session.get(College, lot.college_id)
    qty = body.qty or lot.qty
    lot.status = "listed"
    session.add(lot)
    l = SurplusListing(college_id=lot.college_id, kind="stock_to_colleges", lot_id=lot.id, title=f"{p.name} × {qty:g} packs",
                       qty=qty, qty_remaining=qty, price=body.price, location=col.name, created_at=datetime.now(),
                       available_until=datetime.combine(min(lot.expiry_date, date.today() + timedelta(days=3)),
                                                        datetime.min.time()) + timedelta(hours=17))
    session.add(l)
    session.commit()
    session.refresh(l)
    return l.model_dump()


# ------------------------------------------------------------------ Inter-college marketplace
@router.get("/marketplace")
def marketplace(college_id: int = HOME_COLLEGE_ID, session: Session = Depends(get_session)):
    rows = session.exec(select(SurplusListing).where(SurplusListing.kind == "stock_to_colleges",
                                                     SurplusListing.status == "open")
                        .order_by(SurplusListing.created_at.desc())).all()
    today = date.today()
    out = []
    for l in rows:
        lot = session.get(InventoryLot, l.lot_id)
        p = session.get(Product, lot.product_id)
        seller = session.get(College, l.college_id)
        item = {**l.model_dump(), "seller": seller.short, "seller_colour": seller.colour, "product": p.name,
                "product_id": p.id, "unit": p.unit, "pack_size": p.pack_size, "storage_type": p.storage_type,
                "expiry_date": lot.expiry_date.isoformat(), "days_to_expiry": (lot.expiry_date - today).days,
                "list_price": p.price, "discount_pct": round(100 * (1 - l.price / p.price)) if p.price else 0,
                "mine": l.college_id == college_id}
        if l.college_id != college_id:
            item["fit"] = fit_check(session, college_id, p, l.qty_remaining)
        out.append(item)
    return out


class BuyIn(BaseModel):
    college_id: int = HOME_COLLEGE_ID
    qty: Optional[float] = None


@router.post("/marketplace/{listing_id}/buy")
def buy(listing_id: int, body: BuyIn, session: Session = Depends(get_session)):
    l = session.get(SurplusListing, listing_id)
    if not l or l.status != "open":
        raise HTTPException(404, "Listing no longer available")
    qty = body.qty or l.qty_remaining
    seller_lot = session.get(InventoryLot, l.lot_id)
    p = session.get(Product, seller_lot.product_id)
    fit = fit_check(session, body.college_id, p, qty)
    if not fit["fits"]:
        raise HTTPException(409, fit["reason"])
    l.qty_remaining -= qty
    seller_lot.qty -= qty
    if l.qty_remaining <= 0:
        l.status = "sold_out"
        seller_lot.status = "transferred"
    new_lot = InventoryLot(college_id=body.college_id, product_id=p.id, storage_unit_id=fit["unit_id"], qty=qty,
                           received_at=datetime.now(), expiry_date=seller_lot.expiry_date, source="transfer",
                           transfer_from_college_id=l.college_id)
    c = Claim(listing_id=l.id, buyer_college_id=body.college_id, qty=qty, amount_gbp=round(qty * l.price, 2),
              pickup_code=f"{random.randint(100, 999)}", created_at=datetime.now())
    session.add_all([l, seller_lot, new_lot, c])
    session.commit()
    session.refresh(new_lot)
    session.refresh(c)
    return {"lot": new_lot.model_dump(), "claim": c.model_dump(), "fit": fit}


# ------------------------------------------------------------------ Journey (ontology lineage of one lot)
@router.get("/journey/{lot_id}")
def journey(lot_id: int, session: Session = Depends(get_session)):
    lot = session.get(InventoryLot, lot_id)
    if not lot:
        raise HTTPException(404)
    p = session.get(Product, lot.product_id)
    sup = session.get(Supplier, p.supplier_id)
    col = session.get(College, lot.college_id)
    steps = []
    if lot.source == "transfer":
        src = session.get(College, lot.transfer_from_college_id)
        steps.append({"kind": "transfer", "when": lot.received_at.isoformat(), "title": f"Bought from {src.name} on the OxFood marketplace",
                      "detail": "Surplus that would otherwise have been wasted at another college."})
    if lot.order_id:
        o = session.get(Order, lot.order_id)
        if o:
            steps.append({"kind": "order", "when": o.created_at.isoformat(), "title": f"Ordered from {sup.name}",
                          "detail": f"Order OXF-{o.id:05d}, sent to Foodbuy as CSV, for delivery {o.delivery_date.isoformat()}"})
    issues = session.exec(select(SupplierIssue).where(SupplierIssue.college_id == lot.college_id,
                                                      SupplierIssue.supplier_id == sup.id,
                                                      SupplierIssue.date == lot.received_at.date())).all()
    steps.append({"kind": "delivery", "when": lot.received_at.isoformat(), "title": f"Delivered to {col.short}",
                  "detail": f"{lot.qty:g} × {p.pack_size:g}{p.unit} packs. Use by {lot.expiry_date.isoformat()}."
                            + (f" Issue: {issues[0].type}: {issues[0].notes}" if issues else ""), "issue": bool(issues)})
    unit = session.get(StorageUnit, lot.storage_unit_id) if lot.storage_unit_id else None
    if unit:
        steps.append({"kind": "storage", "when": lot.received_at.isoformat(), "title": f"Stored in {unit.name}",
                      "detail": f"{p.volume_l * lot.qty:.0f} litres of {unit.type} space"})
    recipe_ids = [ri.recipe_id for ri in session.exec(select(RecipeIngredient).where(RecipeIngredient.product_id == p.id)).all()]
    svcs = session.exec(select(Service).where(Service.college_id == lot.college_id, Service.date >= lot.received_at.date(),
                                              Service.date <= min(lot.expiry_date, date.today()))).all()
    for svc in sorted(svcs, key=lambda s: (s.date, s.meal))[:6]:
        used = [rid for rid in svc.recipe_ids if rid in recipe_ids]
        if not used:
            continue
        r = session.get(Recipe, used[0])
        steps.append({"kind": "cooked", "when": f"{svc.date.isoformat()}T12:00:00",
                      "title": f"Cooked into {r.name}", "detail": f"{svc.meal.title()} · {svc.attended or svc.booked} covers"})
        for w in session.exec(select(WasteEvent).where(WasteEvent.service_id == svc.id, WasteEvent.recipe_id == r.id)).all():
            label = {"offer_students": "sold to students", "chill_reuse": "blast-chilled for reuse",
                     "discard": "binned", "compost": "composted"}.get(w.disposition, w.disposition)
            steps.append({"kind": "waste" if w.disposition in ("discard", "compost") else "recovered",
                          "when": w.logged_at.isoformat(), "title": f"{w.weight_kg:g} kg {w.stage.replace('_', ' ')}: {label}",
                          "detail": f"≈{w.portions_est} portions, £{w.value_gbp:.2f}"})
            for lst in session.exec(select(SurplusListing).where(SurplusListing.waste_event_id == w.id)).all():
                claims = session.exec(select(Claim).where(Claim.listing_id == lst.id)).all()
                steps.append({"kind": "recovered", "when": lst.created_at.isoformat(),
                              "title": f"Offered to students at £{lst.price:.2f}",
                              "detail": f"{sum(c.qty for c in claims):g} of {lst.qty:g} portions claimed"})
    return {"lot": lot.model_dump(), "product": p.model_dump(), "supplier": sup.name, "college": col.name,
            "status": lot.status, "steps": steps}
