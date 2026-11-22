"""Suggested order: upcoming menu × forecast covers − in-date stock, rounded up to packs."""
import math
from collections import defaultdict
from datetime import date, timedelta

from sqlmodel import Session, select

from app.models import CollegeSupplier, InventoryLot, Product, RecipeIngredient, Service, Supplier
from app.services.forecast import forecast_service
from app.services.storage import fit_check


def suggested_order(session: Session, college_id: int, days: int = 3, start: date | None = None) -> dict:
    start = start or date.today() + timedelta(days=1)
    end = start + timedelta(days=days - 1)
    services = session.exec(select(Service).where(Service.college_id == college_id, Service.date >= start,
                                                  Service.date <= end)).all()
    active_suppliers = {cs.supplier_id for cs in session.exec(
        select(CollegeSupplier).where(CollegeSupplier.college_id == college_id, CollegeSupplier.active)).all()}

    need: dict[int, float] = defaultdict(float)  # product_id → units needed
    for svc in services:
        fc = forecast_service(session, svc)
        n_mains = max(1, len(svc.recipe_ids) - (1 if svc.meal == "dinner" else 0))
        for i, rid in enumerate(svc.recipe_ids):
            share = 0.5 if (svc.meal == "dinner" and i == len(svc.recipe_ids) - 1) else 1 / n_mains
            portions = fc["recommended_portions"] * share
            for ing in session.exec(select(RecipeIngredient).where(RecipeIngredient.recipe_id == rid)).all():
                need[ing.product_id] += ing.qty_per_portion * portions

    lines = []
    for pid, units in need.items():
        p = session.get(Product, pid)
        stock_packs = sum(l.qty for l in session.exec(select(InventoryLot).where(
            InventoryLot.college_id == college_id, InventoryLot.product_id == pid, InventoryLot.status == "in_stock",
            InventoryLot.expiry_date >= start)).all())
        need_packs = units / p.pack_size
        to_buy = math.ceil(max(0.0, need_packs - stock_packs) - 1e-9)
        if to_buy <= 0:
            continue
        sup = session.get(Supplier, p.supplier_id)
        lines.append({
            "product_id": pid, "sku": p.sku, "name": p.name, "supplier": sup.name, "supplier_active": sup.id in active_suppliers,
            "unit": p.unit, "pack_size": p.pack_size, "needed_units": round(units, 1), "in_stock_packs": stock_packs,
            "qty": to_buy, "unit_price": p.price, "line_total": round(to_buy * p.price, 2),
            "fit": fit_check(session, college_id, p, to_buy),
        })
    lines.sort(key=lambda l: (l["supplier"], l["name"]))
    return {"start": start.isoformat(), "end": end.isoformat(), "services": len(services), "lines": lines,
            "total": round(sum(l["line_total"] for l in lines), 2)}
