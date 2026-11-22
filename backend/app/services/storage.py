"""Physical storage: capacity, free space and 'what can be stored with what'."""
from sqlmodel import Session, select

from app.models import InventoryLot, Product, StorageUnit

UNIT_LABEL = {"fridge": "fridge", "freezer": "freezer", "dry": "dry store"}
STORAGE_FOR = {"chilled": "fridge", "frozen": "freezer", "dry": "dry", "ambient": "dry"}


def unit_usage(session: Session, college_id: int) -> list[dict]:
    units = session.exec(select(StorageUnit).where(StorageUnit.college_id == college_id)).all()
    lots = session.exec(select(InventoryLot, Product).join(Product)
                        .where(InventoryLot.college_id == college_id,
                               InventoryLot.status.in_(["in_stock", "listed"]))).all()
    used: dict[int, float] = {}
    contents: dict[int, list[dict]] = {}
    for lot, p in lots:
        if lot.storage_unit_id is None:
            continue
        used[lot.storage_unit_id] = used.get(lot.storage_unit_id, 0) + lot.qty * p.volume_l
        contents.setdefault(lot.storage_unit_id, []).append({"hazard": p.hazard_class, "name": p.name})
    out = []
    for u in units:
        u_used = round(used.get(u.id, 0), 1)
        out.append({
            "id": u.id, "name": u.name, "type": u.type, "capacity_l": u.capacity_l, "used_l": u_used,
            "free_l": round(u.capacity_l - u_used, 1), "pct": round(100 * u_used / u.capacity_l) if u.capacity_l else 0,
            "warnings": compatibility_warnings([c["hazard"] for c in contents.get(u.id, [])], u.type),
        })
    return out


def compatibility_warnings(hazards: list[str], unit_type: str) -> list[str]:
    hs = set(hazards)
    w = []
    if unit_type == "fridge" and ({"raw_meat", "raw_fish"} & hs) and "ready_to_eat" in hs:
        w.append("Raw meat/fish shares a fridge with ready-to-eat food: keep raw items on the bottom shelves.")
    if "allergen_nuts" in hs and len(hs) > 1:
        w.append("Nut allergens present: store sealed and segregated.")
    return w


def fit_check(session: Session, college_id: int, product: Product, packs: float) -> dict:
    """Can `packs` of `product` physically and safely go into this college's storage?"""
    unit_type = STORAGE_FOR.get(product.storage_type, "dry")
    usage = [u for u in unit_usage(session, college_id) if u["type"] == unit_type]
    need = round(product.volume_l * packs, 1)
    best = max(usage, key=lambda u: u["free_l"], default=None)
    if best is None:
        return {"fits": False, "need_l": need, "unit_type": UNIT_LABEL[unit_type], "reason": f"No {unit_type} space recorded"}
    fits = best["free_l"] >= need
    warnings = []
    if product.hazard_class in ("raw_meat", "raw_fish"):
        warnings.append("Raw product: store below ready-to-eat items.")
    if product.hazard_class == "allergen_nuts":
        warnings.append("Contains nuts: keep sealed and segregated.")
    return {
        "fits": fits, "need_l": need, "unit_type": UNIT_LABEL[unit_type], "unit_id": best["id"], "unit_name": best["name"],
        "free_l": best["free_l"], "free_after_l": round(best["free_l"] - need, 1), "warnings": warnings,
        "reason": (f"Needs {need} l in the {best['name'].lower()}, which has {best['free_l']} l free."
                   if fits else f"Needs {need} l but the {best['name'].lower()} only has {best['free_l']} l free."),
    }
