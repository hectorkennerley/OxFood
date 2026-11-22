import os
import tempfile

os.environ["OXFOOD_DB"] = os.path.join(tempfile.mkdtemp(), "test.db")
os.environ["AI_MODE"] = "off"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.services.ai import parse_waste_rules  # noqa: E402
from app.services.foodbuy_csv import COLUMNS, order_to_csv  # noqa: E402
from app.services.safety_rules import ReuseInput, advise  # noqa: E402


def dispositions(i):
    return [o.disposition for o in advise(i).options]


# ---------------------------------------------------------------- safety rules
def test_plate_waste_never_reused():
    assert dispositions(ReuseInput(stage="plate_waste")) == ["compost"]


def test_past_use_by_is_blocked():
    a = advise(ReuseInput(stage="unopened_stock", past_use_by=True))
    assert [o.disposition for o in a.options] == ["compost"] and a.blocked


def test_overproduction_with_blast_chiller_can_be_chilled():
    d = dispositions(ReuseInput(stage="overproduction", blast_chiller=True, minutes_since_cooked=30))
    assert "chill_reuse" in d and "offer_students" in d


def test_rice_gets_24h_limit():
    a = advise(ReuseInput(stage="overproduction", blast_chiller=True, high_risk=True))
    chill = next(o for o in a.options if o.disposition == "chill_reuse")
    assert chill.use_within_hours == 24


def test_no_blast_chiller_means_no_chill_reuse():
    a = advise(ReuseInput(stage="overproduction", blast_chiller=False))
    assert "chill_reuse" not in [o.disposition for o in a.options] and a.blocked


def test_servery_leftover_cannot_be_chilled():
    d = dispositions(ReuseInput(stage="servery_leftover", blast_chiller=True))
    assert "chill_reuse" not in d and "offer_students" in d


def test_cold_held_over_two_hours_is_discarded():
    assert dispositions(ReuseInput(stage="overproduction", hot_held_63=False, minutes_since_cooked=150)) == ["compost"]


# ---------------------------------------------------------------- voice fallback parser
DISHES = [{"id": 6, "name": "Chicken tikka masala & rice"}, {"id": 14, "name": "Penne arrabbiata (vegan)"}]


@pytest.mark.parametrize("text,dish,stage,kg", [
    ("about three kilos of chicken tikka never left the kitchen", 6, "overproduction", 3.0),
    ("2.5kg of penne left on the servery", 14, "servery_leftover", 2.5),
    ("800 grams of plate waste", None, "plate_waste", 0.8),
    ("deux kilos de restes de poulet tikka", 6, "servery_leftover", 2.0),
])
def test_parse_waste_rules(text, dish, stage, kg):
    r = parse_waste_rules(text, DISHES)
    assert (r["dish_id"], r["stage"], r["weight_kg"]) == (dish, stage, kg)


def test_foodbuy_csv_layout():
    csv_text = order_to_csv("OXF-1", "St Edmund Hall", "SEH", "2026-01-01", [
        {"supplier_code": "CFP", "supplier_name": "Cherwell", "sku": "X", "name": "Spinach", "pack_size": 2,
         "unit": "kg", "qty": 3, "unit_price": 7.5}])
    header, row = csv_text.strip().splitlines()
    assert header.split(",") == COLUMNS
    assert row.endswith(",3,7.50,22.50")


# ---------------------------------------------------------------- golden path through the API
@pytest.fixture(scope="module")
def client():
    from app.main import app

    with TestClient(app) as c:
        yield c


def test_golden_path(client):
    lunch = next(s for s in client.get("/api/services/today").json() if s["meal"] == "lunch")
    dish = lunch["dishes"][0]

    parsed = client.post("/api/ai/parse-waste", json={"transcript": "three kilos of chicken tikka never left the kitchen",
                                                      "service_id": lunch["id"]}).json()
    assert parsed["source"] == "rules" and parsed["dish_id"] == dish["id"]

    before = client.get("/api/analytics/dashboard").json()["this_week"]["kg"]
    logged = client.post("/api/waste", json={"service_id": lunch["id"], "recipe_id": dish["id"],
                                             "stage": "overproduction", "weight_kg": 3}).json()
    assert logged["offer"]["portions"] > 0
    assert any(o["disposition"] == "offer_students" for o in logged["advice"]["options"])

    listing = client.post("/api/listings/offer", json={"waste_event_id": logged["event"]["id"], "portions": 6,
                                                       "price": 2.5}).json()
    feed = client.get("/api/student/feed").json()
    assert any(l["id"] == listing["id"] for l in feed["listings"])
    assert client.post(f"/api/listings/{listing['id']}/claim", json={"qty": 1}).json()["claim"]["amount_gbp"] == 2.5

    after = client.get("/api/analytics/dashboard").json()["this_week"]
    assert after["kg"] == pytest.approx(before + 3, abs=0.05)
    assert after["gbp_sales"] >= 2.5


def test_marketplace_buy_creates_transfer_lot(client):
    item = next(l for l in client.get("/api/marketplace").json() if not l["mine"] and l["fit"]["fits"])
    r = client.post(f"/api/marketplace/{item['id']}/buy", json={}).json()
    assert r["lot"]["source"] == "transfer" and r["claim"]["amount_gbp"] > 0
    j = client.get(f"/api/journey/{r['lot']['id']}").json()
    assert j["steps"][0]["kind"] == "transfer"


def test_order_and_csv(client):
    sugg = client.get("/api/orders/suggested?days=3").json()
    assert sugg["lines"], "menu plan should need some ingredients"
    lines = [{"product_id": l["product_id"], "qty": l["qty"]} for l in sugg["lines"][:3]]
    o = client.post("/api/orders", json={"lines": lines}).json()
    r = client.get(f"/api/orders/{o['id']}/foodbuy.csv")
    assert r.status_code == 200 and r.text.startswith("OrderRef,")
