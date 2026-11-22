"""Deterministic fabricated demo data. Run:  python -m app.seed

Everything is generated relative to *today* so the demo story works on any day.
Suppliers are fictional; all numbers are simulated.
"""
import hashlib
import random
from collections import defaultdict
from datetime import date, datetime, time, timedelta

from sqlmodel import Session, SQLModel

from app.db import engine, init_db
from app.models import (
    Appliance, Attendance, Claim, College, CollegeSupplier, InventoryLot, Notification, Order,
    OrderLine, Product, Recipe, RecipeIngredient, Service, StorageUnit, Student, SupplierIssue,
    Supplier, SurplusListing, WasteEvent,
)

HISTORY_DAYS = 56
GO_LIVE_DAYS_AGO = 28  # OxFood "switched on" four weeks ago → trend improves after this
FUTURE_DAYS = 7

COLLEGES = [
    ("St Edmund Hall", "Teddy Hall", "#7a1f2b", "SEH-CAT-01", 1.0),
    ("Keble College", "Keble", "#0b3d91", "KEB-CAT-01", 1.25),
    ("Balliol College", "Balliol", "#1a5e3a", "BAL-CAT-01", 1.1),
    ("Lincoln College", "Lincoln", "#5c2d82", "LIN-CAT-01", 0.8),
    ("Exeter College", "Exeter", "#b35900", "EXE-CAT-01", 0.9),
]

SUPPLIERS = [
    ("CFP", "Cherwell Fresh Produce", "produce", 1),
    ("ISD", "Isis Dairy", "dairy", 1),
    ("TVM", "Thames Valley Meats", "meat", 2),
    ("PMB", "Port Meadow Bakery", "bakery", 1),
    ("RDG", "Radcliffe Dry Goods", "dry", 3),
    ("CFS", "Cotswold Fish Co.", "fish", 2),
    ("BFR", "Botley Frozen Foods", "frozen", 3),
]

# supplier, sku, name, category, unit, pack_size, £/pack, storage, litres/pack, shelf_days, hazard, allergens, freezable
PRODUCTS = [
    ("CFP", "CFP-POT25", "Potatoes (maris piper)", "veg", "kg", 25, 12.0, "dry", 30, 21, "produce", [], False),
    ("CFP", "CFP-ONI20", "Brown onions", "veg", "kg", 20, 11.0, "dry", 26, 28, "produce", [], False),
    ("CFP", "CFP-CAR10", "Carrots", "veg", "kg", 10, 7.0, "chilled", 13, 14, "produce", [], False),
    ("CFP", "CFP-LEE05", "Leeks", "veg", "kg", 5, 8.0, "chilled", 9, 10, "produce", [], False),
    ("CFP", "CFP-SPI02", "Baby spinach", "veg", "kg", 2, 7.5, "chilled", 8, 4, "produce", [], False),
    ("CFP", "CFP-KAL02", "Curly kale", "veg", "kg", 2, 6.5, "chilled", 8, 6, "produce", [], False),
    ("CFP", "CFP-TOM06", "Vine tomatoes", "veg", "kg", 6, 10.0, "chilled", 9, 7, "produce", [], False),
    ("CFP", "CFP-PEP05", "Mixed peppers", "veg", "kg", 5, 11.0, "chilled", 9, 8, "produce", [], False),
    ("CFP", "CFP-MUS25", "Closed cup mushrooms", "veg", "kg", 2.5, 7.0, "chilled", 7, 5, "produce", [], False),
    ("CFP", "CFP-BRO05", "Broccoli", "veg", "kg", 5, 9.0, "chilled", 10, 6, "produce", [], False),
    ("CFP", "CFP-LET01", "Mixed salad leaves", "veg", "kg", 1, 6.0, "chilled", 6, 4, "produce", [], False),
    ("CFP", "CFP-GAR01", "Garlic", "veg", "kg", 1, 6.0, "dry", 2, 30, "produce", [], False),
    ("CFP", "CFP-APP10", "Bramley apples", "fruit", "kg", 10, 13.0, "chilled", 14, 21, "produce", [], False),
    ("CFP", "CFP-BAN13", "Bananas", "fruit", "kg", 13, 14.0, "dry", 18, 6, "produce", [], False),
    ("CFP", "CFP-BUT10", "Butternut squash", "veg", "kg", 10, 11.0, "dry", 14, 30, "produce", [], False),
    ("CFP", "CFP-COU05", "Courgettes", "veg", "kg", 5, 8.0, "chilled", 8, 7, "produce", [], False),
    ("ISD", "ISD-MIL12", "Semi-skimmed milk", "dairy", "l", 12, 11.0, "chilled", 14, 8, "dairy", ["milk"], False),
    ("ISD", "ISD-BUT05", "Unsalted butter", "dairy", "kg", 5, 32.0, "chilled", 6, 60, "dairy", ["milk"], True),
    ("ISD", "ISD-CHE05", "Mature cheddar", "dairy", "kg", 5, 30.0, "chilled", 6, 45, "dairy", ["milk"], True),
    ("ISD", "ISD-CRE05", "Double cream", "dairy", "l", 5, 18.0, "chilled", 6, 9, "dairy", ["milk"], False),
    ("ISD", "ISD-EGG180", "Free-range eggs", "dairy", "each", 180, 36.0, "chilled", 22, 21, "dairy", ["eggs"], False),
    ("ISD", "ISD-YOG05", "Greek yoghurt", "dairy", "kg", 5, 15.0, "chilled", 6, 14, "dairy", ["milk"], False),
    ("ISD", "ISD-MOZ02", "Mozzarella", "dairy", "kg", 2, 14.0, "chilled", 3, 14, "dairy", ["milk"], True),
    ("ISD", "ISD-PAR01", "Parmesan", "dairy", "kg", 1, 16.0, "chilled", 1.5, 60, "dairy", ["milk"], True),
    ("TVM", "TVM-CTH05", "Chicken thighs (boneless)", "meat", "kg", 5, 27.0, "chilled", 7, 5, "raw_meat", [], True),
    ("TVM", "TVM-CBR05", "Chicken breast", "meat", "kg", 5, 35.0, "chilled", 7, 5, "raw_meat", [], True),
    ("TVM", "TVM-WCH08", "Whole chickens", "meat", "kg", 8, 30.0, "chilled", 14, 5, "raw_meat", [], True),
    ("TVM", "TVM-MIN05", "Beef mince (15%)", "meat", "kg", 5, 34.0, "chilled", 6, 4, "raw_meat", [], True),
    ("TVM", "TVM-BRA05", "Braising beef", "meat", "kg", 5, 48.0, "chilled", 6, 6, "raw_meat", [], True),
    ("TVM", "TVM-SAU05", "Pork sausages", "meat", "kg", 5, 26.0, "chilled", 7, 7, "raw_meat", ["gluten"], True),
    ("TVM", "TVM-BAC25", "Back bacon", "meat", "kg", 2.5, 18.0, "chilled", 4, 10, "raw_meat", [], True),
    ("TVM", "TVM-LAM05", "Lamb shoulder", "meat", "kg", 5, 55.0, "chilled", 7, 6, "raw_meat", [], True),
    ("PMB", "PMB-LOA10", "White sliced loaves", "bakery", "each", 10, 14.0, "dry", 30, 4, "ready_to_eat", ["gluten"], True),
    ("PMB", "PMB-CRO48", "All-butter croissants", "bakery", "each", 48, 22.0, "dry", 40, 2, "ready_to_eat", ["gluten", "milk"], True),
    ("PMB", "PMB-BUN48", "Brioche burger buns", "bakery", "each", 48, 12.0, "dry", 35, 4, "ready_to_eat", ["gluten", "eggs"], True),
    ("PMB", "PMB-WRA72", "Flour tortilla wraps", "bakery", "each", 72, 14.0, "dry", 8, 14, "ready_to_eat", ["gluten"], True),
    ("PMB", "PMB-SOU06", "Sourdough loaves", "bakery", "each", 6, 15.0, "dry", 18, 3, "ready_to_eat", ["gluten"], True),
    ("RDG", "RDG-RIC10", "Basmati rice", "dry", "kg", 10, 18.0, "dry", 12, 365, "general", [], False),
    ("RDG", "RDG-PEN06", "Penne pasta", "dry", "kg", 6, 9.0, "dry", 12, 365, "general", ["gluten"], False),
    ("RDG", "RDG-LAS05", "Lasagne sheets", "dry", "kg", 5, 9.5, "dry", 8, 365, "general", ["gluten", "eggs"], False),
    ("RDG", "RDG-FLO16", "Plain flour", "dry", "kg", 16, 11.0, "dry", 22, 270, "general", ["gluten"], False),
    ("RDG", "RDG-TTO15", "Chopped tomatoes (tins)", "dry", "kg", 15, 14.0, "dry", 14, 540, "general", [], False),
    ("RDG", "RDG-COC06", "Coconut milk", "dry", "l", 6, 12.0, "dry", 7, 365, "general", [], False),
    ("RDG", "RDG-CHI15", "Chickpeas (tins)", "dry", "kg", 15, 13.0, "dry", 14, 540, "general", [], False),
    ("RDG", "RDG-LEN05", "Red lentils", "dry", "kg", 5, 9.0, "dry", 6, 365, "general", [], False),
    ("RDG", "RDG-OAT05", "Porridge oats", "dry", "kg", 5, 6.0, "dry", 9, 270, "general", ["gluten"], False),
    ("RDG", "RDG-OIL20", "Rapeseed oil", "dry", "l", 20, 32.0, "dry", 22, 365, "general", [], False),
    ("RDG", "RDG-CUR02", "Tikka curry paste", "dry", "kg", 2, 14.0, "dry", 2.5, 180, "general", ["mustard"], False),
    ("RDG", "RDG-STO02", "Vegetable stock powder", "dry", "kg", 2, 12.0, "dry", 3, 365, "general", ["celery"], False),
    ("RDG", "RDG-SUG05", "Caster sugar", "dry", "kg", 5, 5.0, "dry", 6, 730, "general", [], False),
    ("RDG", "RDG-GRA05", "Granola", "dry", "kg", 5, 16.0, "dry", 12, 180, "allergen_nuts", ["gluten", "nuts"], False),
    ("RDG", "RDG-PBU02", "Peanut butter", "dry", "kg", 2, 9.0, "dry", 2.5, 270, "allergen_nuts", ["peanuts"], False),
    ("RDG", "RDG-NOO05", "Egg noodles", "dry", "kg", 5, 10.0, "dry", 9, 365, "general", ["gluten", "eggs"], False),
    ("CFS", "CFS-SAL05", "Salmon fillets", "fish", "kg", 5, 60.0, "chilled", 6, 3, "raw_fish", ["fish"], True),
    ("CFS", "CFS-COD05", "Cod loin", "fish", "kg", 5, 55.0, "chilled", 6, 3, "raw_fish", ["fish"], True),
    ("CFS", "CFS-HAD02", "Smoked haddock", "fish", "kg", 2, 22.0, "chilled", 3, 5, "raw_fish", ["fish"], True),
    ("BFR", "BFR-PEA10", "Garden peas (frozen)", "frozen", "kg", 10, 12.0, "frozen", 13, 365, "general", [], False),
    ("BFR", "BFR-CHP12", "Chunky chips (frozen)", "frozen", "kg", 12, 16.0, "frozen", 18, 365, "general", [], False),
    ("BFR", "BFR-FCT10", "Chicken thighs (frozen)", "frozen", "kg", 10, 45.0, "frozen", 12, 270, "raw_meat", [], False),
    ("BFR", "BFR-ICE05", "Vanilla ice cream", "frozen", "l", 5, 15.0, "frozen", 6, 365, "ready_to_eat", ["milk"], False),
    ("BFR", "BFR-BER05", "Mixed berries (frozen)", "frozen", "kg", 5, 18.0, "frozen", 6, 365, "general", [], False),
    ("BFR", "BFR-SWE10", "Sweetcorn (frozen)", "frozen", "kg", 10, 12.0, "frozen", 13, 365, "general", [], False),
]

HOT = ["prep", "cook", "hot_hold", "servery"]
COLD = ["prep", "chill", "servery"]

# name, meal, portion_g, price, high_risk, stages, appliances, allergens, emoji, [(sku, qty_per_portion)]
RECIPES = [
    ("Full English breakfast", "breakfast", 350, 4.20, False, HOT, ["hob", "combi_oven"], ["gluten", "eggs"], "🍳",
     [("TVM-SAU05", 0.1), ("TVM-BAC25", 0.05), ("ISD-EGG180", 1), ("CFP-TOM06", 0.05), ("CFP-MUS25", 0.04)]),
    ("Porridge with berries", "breakfast", 300, 1.80, False, ["prep", "cook", "servery"], ["hob"], ["gluten", "milk"], "🥣",
     [("RDG-OAT05", 0.05), ("ISD-MIL12", 0.2), ("BFR-BER05", 0.04)]),
    ("Granola & Greek yoghurt", "breakfast", 220, 2.20, False, COLD, [], ["gluten", "nuts", "milk"], "🥛",
     [("RDG-GRA05", 0.06), ("ISD-YOG05", 0.15)]),
    ("Scrambled eggs on sourdough", "breakfast", 250, 2.80, False, HOT, ["hob"], ["gluten", "eggs", "milk"], "🍞",
     [("ISD-EGG180", 2), ("PMB-SOU06", 0.12), ("ISD-BUT05", 0.01)]),
    ("Croissant & fruit", "breakfast", 180, 2.00, False, ["servery"], [], ["gluten", "milk"], "🥐",
     [("PMB-CRO48", 1), ("CFP-BAN13", 0.12)]),
    ("Chicken tikka masala & rice", "lunch", 450, 5.20, True, HOT, ["bratt_pan", "combi_oven"], ["milk", "mustard"], "🍛",
     [("TVM-CTH05", 0.15), ("RDG-RIC10", 0.08), ("RDG-CUR02", 0.02), ("RDG-TTO15", 0.06), ("CFP-ONI20", 0.05), ("ISD-CRE05", 0.02)]),
    ("Beef lasagne & salad", "dinner", 420, 5.50, False, HOT, ["combi_oven"], ["gluten", "eggs", "milk"], "🍝",
     [("TVM-MIN05", 0.13), ("RDG-LAS05", 0.06), ("RDG-TTO15", 0.08), ("ISD-CHE05", 0.03), ("ISD-MIL12", 0.08), ("CFP-LET01", 0.03)]),
    ("Chilli con carne & rice", "lunch", 450, 4.90, True, HOT, ["bratt_pan"], [], "🌶️",
     [("TVM-MIN05", 0.12), ("RDG-RIC10", 0.08), ("RDG-TTO15", 0.08), ("CFP-PEP05", 0.04), ("CFP-ONI20", 0.04)]),
    ("Roast chicken, potatoes & greens", "dinner", 480, 6.20, False, HOT, ["combi_oven"], [], "🍗",
     [("TVM-WCH08", 0.25), ("CFP-POT25", 0.2), ("CFP-BRO05", 0.08), ("CFP-CAR10", 0.06)]),
    ("Fish pie", "dinner", 420, 6.40, False, HOT, ["combi_oven"], ["fish", "milk"], "🥧",
     [("CFS-COD05", 0.08), ("CFS-HAD02", 0.04), ("CFP-POT25", 0.2), ("ISD-MIL12", 0.08), ("ISD-BUT05", 0.015), ("BFR-PEA10", 0.05)]),
    ("Salmon, new potatoes & broccoli", "dinner", 400, 7.20, True, HOT, ["combi_oven", "steamer"], ["fish"], "🐟",
     [("CFS-SAL05", 0.14), ("CFP-POT25", 0.18), ("CFP-BRO05", 0.08)]),
    ("Lamb & chickpea tagine", "dinner", 450, 6.80, False, HOT, ["bratt_pan"], [], "🍲",
     [("TVM-LAM05", 0.14), ("RDG-CHI15", 0.08), ("RDG-TTO15", 0.06), ("CFP-ONI20", 0.04), ("RDG-RIC10", 0.07)]),
    ("Butternut squash risotto", "lunch", 400, 4.60, True, HOT, ["hob"], ["milk", "celery"], "🎃",
     [("CFP-BUT10", 0.15), ("RDG-RIC10", 0.08), ("ISD-PAR01", 0.02), ("RDG-STO02", 0.01)]),
    ("Penne arrabbiata (vegan)", "lunch", 400, 3.90, False, HOT, ["hob"], ["gluten"], "🍅",
     [("RDG-PEN06", 0.1), ("RDG-TTO15", 0.1), ("CFP-GAR01", 0.01), ("RDG-OIL20", 0.01)]),
    ("Mushroom stroganoff & rice", "dinner", 420, 4.80, True, HOT, ["hob"], ["milk"], "🍄",
     [("CFP-MUS25", 0.15), ("ISD-CRE05", 0.04), ("RDG-RIC10", 0.08), ("CFP-ONI20", 0.04)]),
    ("Chickpea & spinach curry (vegan)", "lunch", 420, 4.20, True, HOT, ["bratt_pan"], ["mustard"], "🥘",
     [("RDG-CHI15", 0.12), ("CFP-SPI02", 0.05), ("RDG-COC06", 0.06), ("RDG-CUR02", 0.015), ("RDG-RIC10", 0.08)]),
    ("Sausage & mash with peas", "dinner", 450, 4.80, False, HOT, ["combi_oven", "hob"], ["gluten", "milk"], "🌭",
     [("TVM-SAU05", 0.15), ("CFP-POT25", 0.22), ("ISD-BUT05", 0.01), ("BFR-PEA10", 0.06)]),
    ("Fish & chips", "lunch", 450, 6.00, False, ["prep", "cook", "hot_hold", "servery"], ["fryer"], ["fish", "gluten"], "🐠",
     [("CFS-COD05", 0.15), ("BFR-CHP12", 0.2), ("RDG-FLO16", 0.03), ("BFR-PEA10", 0.06)]),
    ("Chicken Caesar wrap", "lunch", 300, 4.50, False, COLD, ["combi_oven"], ["gluten", "eggs", "milk", "fish"], "🌯",
     [("TVM-CBR05", 0.1), ("PMB-WRA72", 1), ("CFP-LET01", 0.03), ("ISD-PAR01", 0.01)]),
    ("Leek & potato soup with bread", "lunch", 400, 2.90, False, ["prep", "cook", "hot_hold", "servery"], ["hob"], ["gluten", "milk", "celery"], "🥣",
     [("CFP-LEE05", 0.08), ("CFP-POT25", 0.1), ("RDG-STO02", 0.01), ("PMB-LOA10", 0.1)]),
    ("Beef stew & dumplings", "dinner", 480, 6.30, False, HOT, ["bratt_pan", "combi_oven"], ["gluten", "celery"], "🥩",
     [("TVM-BRA05", 0.15), ("CFP-CAR10", 0.06), ("CFP-ONI20", 0.05), ("RDG-FLO16", 0.04), ("RDG-STO02", 0.01)]),
    ("Shepherd's pie", "dinner", 450, 5.40, False, HOT, ["combi_oven"], ["milk", "celery"], "🥔",
     [("TVM-MIN05", 0.12), ("CFP-POT25", 0.22), ("CFP-CAR10", 0.05), ("ISD-BUT05", 0.01)]),
    ("Vegetable noodle stir-fry", "lunch", 380, 4.10, False, HOT, ["hob"], ["gluten", "eggs", "soya"], "🍜",
     [("RDG-NOO05", 0.09), ("CFP-PEP05", 0.06), ("CFP-COU05", 0.05), ("CFP-BRO05", 0.05)]),
    ("Apple crumble & custard", "dinner", 200, 2.20, False, HOT, ["combi_oven"], ["gluten", "milk"], "🍏",
     [("CFP-APP10", 0.1), ("RDG-FLO16", 0.03), ("ISD-BUT05", 0.015), ("RDG-SUG05", 0.02), ("ISD-MIL12", 0.1)]),
    ("Ice cream & berries", "dinner", 150, 1.80, False, ["servery"], [], ["milk"], "🍨",
     [("BFR-ICE05", 0.1), ("BFR-BER05", 0.04)]),
]

BREAKFAST = ["Full English breakfast", "Porridge with berries", "Granola & Greek yoghurt",
             "Scrambled eggs on sourdough", "Croissant & fruit"]
LUNCH = ["Chicken tikka masala & rice", "Chilli con carne & rice", "Butternut squash risotto",
         "Penne arrabbiata (vegan)", "Chickpea & spinach curry (vegan)", "Fish & chips",
         "Chicken Caesar wrap", "Leek & potato soup with bread", "Vegetable noodle stir-fry"]
DINNER = ["Beef lasagne & salad", "Roast chicken, potatoes & greens", "Fish pie",
          "Salmon, new potatoes & broccoli", "Lamb & chickpea tagine", "Mushroom stroganoff & rice",
          "Sausage & mash with peas", "Beef stew & dumplings", "Shepherd's pie"]
DESSERT = ["Apple crumble & custard", "Ice cream & berries"]

SHOW_RATE = {"breakfast": 0.58, "lunch": 0.80, "dinner": 0.83}
EVENT_SHOW = {"formal_hall": 0.95, "guest_night": 0.97, "brunch": 0.62, "conference": 0.9}
BASE_BOOKED = {"breakfast": 120, "lunch": 215, "dinner": 225}
STAFF = {"breakfast": 4, "lunch": 7, "dinner": 8}


def _event_type(d: date, meal: str) -> str:
    wd = d.weekday()  # Mon=0
    if meal == "dinner" and wd in (1, 3):
        return "formal_hall"
    if meal == "dinner" and wd == 4 and d.isocalendar().week % 2 == 1:
        return "guest_night"
    if meal == "lunch" and wd == 6:
        return "brunch"
    if meal == "lunch" and wd == 2 and d.isocalendar().week % 3 == 0:
        return "conference"
    return "informal"


def _pseudo(college_id: int, n: int) -> str:
    return "S-" + hashlib.sha256(f"{college_id}-{n}".encode()).hexdigest()[:8].upper()


def seed() -> None:
    rng = random.Random(42)
    today = date.today()
    now = datetime.now()
    SQLModel.metadata.drop_all(engine)
    init_db()

    with Session(engine) as s:
        colleges = [College(name=n, short=sh, colour=c, cost_centre=cc) for n, sh, c, cc, _ in COLLEGES]
        s.add_all(colleges)
        suppliers = {code: Supplier(code=code, name=n, category=cat, lead_time_days=lt) for code, n, cat, lt in SUPPLIERS}
        s.add_all(suppliers.values())
        s.flush()

        for col in colleges:
            for code, sup in suppliers.items():
                # Lincoln doesn't buy fish from Cotswold; Exeter doesn't use Botley Frozen
                active = not ((col.short == "Lincoln" and code == "CFS") or (col.short == "Exeter" and code == "BFR"))
                s.add(CollegeSupplier(college_id=col.id, supplier_id=sup.id, active=active))

        products = {}
        for sc, sku, name, cat, unit, ps, price, st, vol, shelf, hz, alg, frz in PRODUCTS:
            p = Product(supplier_id=suppliers[sc].id, sku=sku, name=name, category=cat, unit=unit, pack_size=ps,
                        price=price, storage_type=st, volume_l=vol, shelf_life_days=shelf, hazard_class=hz,
                        allergens=alg, freezable=frz)
            products[sku] = p
        s.add_all(products.values())
        s.flush()

        recipes = {}
        for name, meal, pg, price, hr, stages, apps, alg, emoji, ings in RECIPES:
            cost = sum(products[sku].price / products[sku].pack_size * q for sku, q in ings)
            r = Recipe(name=name, meal_type=meal, portion_g=pg, sell_price=price, cost_per_portion=round(cost, 2),
                       high_risk=hr, stages=stages, appliances=apps, allergens=alg, emoji=emoji)
            recipes[name] = r
            s.add(r)
            s.flush()
            for sku, q in ings:
                s.add(RecipeIngredient(recipe_id=r.id, product_id=products[sku].id, qty_per_portion=q))

        # Storage + appliances
        storage = defaultdict(dict)
        for col, (_, _, _, _, scale) in zip(colleges, COLLEGES):
            for nm, typ, cap in [("Walk-in fridge", "fridge", 1400), ("Dairy & prep fridge", "fridge", 450),
                                 ("Walk-in freezer", "freezer", 900), ("Dry store", "dry", 3200)]:
                su = StorageUnit(college_id=col.id, name=nm, type=typ, capacity_l=round(cap * scale))
                s.add(su)
                s.flush()
                storage[col.id].setdefault(typ, []).append(su)
            apps = [("Combi oven 1", "combi_oven"), ("Combi oven 2", "combi_oven"), ("Bratt pan", "bratt_pan"),
                    ("Fryer", "fryer"), ("Steamer", "steamer"), ("6-ring hob", "hob")]
            if col.short in ("Teddy Hall", "Keble", "Balliol"):
                apps.append(("Blast chiller", "blast_chiller"))
            s.add_all([Appliance(college_id=col.id, name=n, type=t) for n, t in apps])

        # Students for the home college (pseudonymised), each with a personal show-up habit
        home = colleges[0]
        students = []
        for i in range(260):
            st = Student(college_id=home.id, pseudo_id=_pseudo(home.id, i), year=rng.choice(["1st", "2nd", "3rd", "4th", "Grad"]))
            students.append(st)
        s.add_all(students)
        s.flush()
        reliability = {st.id: min(0.99, max(0.2, rng.betavariate(6, 1.6))) for st in students}

        # Services, bookings, attendance, waste
        waste_rows = []
        for col, (_, _, _, _, scale) in zip(colleges, COLLEGES):
            for offset in range(-HISTORY_DAYS, FUTURE_DAYS + 1):
                d = today + timedelta(days=offset)
                wd = d.weekday()
                for meal in ("breakfast", "lunch", "dinner"):
                    if wd == 6 and meal == "breakfast":
                        continue  # Sunday brunch replaces breakfast
                    ev = _event_type(d, meal)
                    menu_pool = {"breakfast": BREAKFAST, "lunch": LUNCH, "dinner": DINNER}[meal]
                    k = 3 if meal != "breakfast" else 3
                    day_rng = random.Random(f"{d.isoformat()}-{meal}-{col.id % 2}")
                    dishes = day_rng.sample(menu_pool, k)
                    if meal == "dinner":
                        dishes.append(day_rng.choice(DESSERT))
                    if meal == "breakfast" and offset == 0:
                        dishes = ["Full English breakfast", "Porridge with berries", "Croissant & fruit"]
                    if meal == "lunch" and offset == 0:
                        dishes = ["Chicken tikka masala & rice", "Penne arrabbiata (vegan)", "Leek & potato soup with bread"]
                    booked_base = BASE_BOOKED[meal] * scale
                    if wd >= 5:
                        booked_base *= 0.75
                    if ev == "formal_hall":
                        booked_base = 185 * scale
                    if ev == "guest_night":
                        booked_base = 200 * scale
                    booked = int(booked_base * rng.uniform(0.92, 1.08))
                    show = EVENT_SHOW.get(ev, SHOW_RATE[meal])
                    if meal == "dinner" and wd == 5:
                        show = 0.66
                    if meal == "dinner" and wd == 4 and ev == "informal":
                        show = 0.72
                    past = offset < 0 or (offset == 0 and meal != "dinner")
                    future = not past
                    if future and offset > 2:
                        booked = int(booked * (0.55 + 0.1 * (FUTURE_DAYS - offset)) if offset < FUTURE_DAYS else booked * 0.5)
                    attended = int(booked * min(1.0, show + rng.uniform(-0.05, 0.05))) if past else 0
                    golive = offset >= -GO_LIVE_DAYS_AGO
                    if golive:
                        # Kitchens get better at trusting the forecast week by week after go-live
                        weeks_live = (offset + GO_LIVE_DAYS_AGO) // 7
                        buf = max(0.03, 0.15 - 0.035 * weeks_live) if ev not in ("formal_hall", "guest_night") else 0.03
                        planned = int(booked * min(1.0, show + buf))
                    else:
                        planned = int(booked * 1.05)
                    svc = Service(college_id=col.id, date=d, meal=meal, event_type=ev, booked=booked, attended=attended,
                                  staff_on_shift=STAFF[meal] + (3 if ev in ("formal_hall", "guest_night") else 0) + (1 if scale > 1.1 else 0),
                                  planned_portions=planned, recipe_ids=[recipes[x].id for x in dishes])
                    s.add(svc)
                    s.flush()

                    # Per-student attendance for the home college, last 28 days
                    if col.id == home.id and past and offset >= -28:
                        bookers = rng.sample(students, min(len(students), booked))
                        scanned = 0
                        for st in bookers:
                            p = reliability[st.id] * (show / 0.8)
                            sc = rng.random() < min(0.99, p)
                            scanned += sc
                            s.add(Attendance(service_id=svc.id, student_id=st.id, booked=True, scanned=sc))
                        svc.attended = scanned

                    if not past:
                        continue
                    # Waste for this service
                    logged = datetime.combine(d, {"breakfast": time(9, 40), "lunch": time(14, 10), "dinner": time(20, 30)}[meal])
                    mains = [x for x in dishes if x not in DESSERT]
                    for dish in dishes:
                        r = recipes[dish]
                        share = 1 / len(mains) if dish in mains else 0.5
                        cooked = svc.planned_portions * share
                        eaten = svc.attended * share * rng.uniform(0.85, 1.12)
                        left = max(0.0, cooked - eaten) + rng.uniform(0, 3)
                        if left < 1:
                            continue
                        serv_portions = left * 0.6
                        over_portions = left * 0.4
                        for stage, portions, mins in (("servery_leftover", serv_portions, 0), ("overproduction", over_portions, 5)):
                            if portions < 1:
                                continue
                            kg = round(portions * r.portion_g / 1000, 2)
                            disp = "discard"
                            if golive:
                                if stage == "overproduction" and col.short in ("Teddy Hall", "Keble", "Balliol"):
                                    disp = rng.choice(["chill_reuse", "chill_reuse", "offer_students", "discard"])
                                elif stage == "servery_leftover":
                                    disp = rng.choice(["offer_students", "discard", "discard"])
                            waste_rows.append(WasteEvent(college_id=col.id, service_id=svc.id, recipe_id=r.id, stage=stage,
                                                         weight_kg=kg, portions_est=int(portions), value_gbp=round(portions * r.cost_per_portion, 2),
                                                         logged_at=logged + timedelta(minutes=mins), method="seed", disposition=disp))
                    # Plate waste and prep trim
                    plate_g = (24 if not golive else 18) * rng.uniform(0.85, 1.15)
                    plate_kg = round(svc.attended * plate_g / 1000, 2)
                    waste_rows.append(WasteEvent(college_id=col.id, service_id=svc.id, stage="plate_waste", weight_kg=plate_kg,
                                                 value_gbp=round(plate_kg * 4.0, 2), logged_at=logged + timedelta(minutes=15),
                                                 method="seed", disposition="compost"))
                    trim_kg = round(rng.uniform(0.8, 2.2) * (1.0 if not golive else 0.8) * scale, 2)
                    waste_rows.append(WasteEvent(college_id=col.id, service_id=svc.id, stage="prep_trim", weight_kg=trim_kg,
                                                 value_gbp=round(trim_kg * 2.5, 2), logged_at=logged - timedelta(hours=3),
                                                 method="seed", disposition="compost" if not golive else rng.choice(["compost", "staff_meal"])))
                    # Occasional spoilage (much rarer after go-live)
                    if rng.random() < (0.25 if not golive else 0.08) and meal == "lunch":
                        prod = rng.choice([p for p in products.values() if p.storage_type == "chilled"])
                        kg = round(prod.pack_size * rng.uniform(0.3, 1.0), 2) if prod.unit != "each" else round(rng.uniform(1, 4), 2)
                        waste_rows.append(WasteEvent(college_id=col.id, service_id=svc.id, product_id=prod.id, stage="spoilage",
                                                     weight_kg=kg, value_gbp=round(prod.price * min(1, kg / max(prod.pack_size, 1)), 2),
                                                     logged_at=logged - timedelta(hours=5), method="seed", disposition="discard",
                                                     note=f"{prod.name} past use-by"))
        s.add_all(waste_rows)
        s.flush()

        # Past student sales of surplus at the home college (last 7 days) so revenue KPIs have history
        for w in waste_rows:
            if (w.college_id == home.id and w.disposition == "offer_students" and w.recipe_id
                    and w.logged_at.date() >= today - timedelta(days=6) and w.portions_est >= 2):
                r = next(x for x in recipes.values() if x.id == w.recipe_id)
                price = max(1.0, round(r.sell_price * 0.5 * 2) / 2)
                sold = max(1, int(w.portions_est * rng.uniform(0.6, 1.0)))
                lst = SurplusListing(college_id=home.id, kind="meal_to_students", recipe_id=r.id, waste_event_id=w.id,
                                     title=r.name, qty=w.portions_est, qty_remaining=w.portions_est - sold, price=price,
                                     created_at=w.logged_at, available_until=w.logged_at + timedelta(minutes=90),
                                     status="closed")
                s.add(lst)
                s.flush()
                for k in range(sold):
                    s.add(Claim(listing_id=lst.id, student_pseudo_id=rng.choice(students).pseudo_id, qty=1, amount_gbp=price,
                                pickup_code=f"{rng.randint(100, 999)}", created_at=w.logged_at + timedelta(minutes=5 + 3 * k)))

        # Orders + inventory lots for every college
        order_cache = {}
        for col in colleges:
            for typ_units in storage[col.id].values():
                pass
            n_lots = 46 if col.id == home.id else 28
            chosen = rng.sample(list(products.values()), n_lots)
            for p in chosen:
                received_ago = rng.randint(0, 6)
                rec_date = today - timedelta(days=received_ago)
                key = (col.id, rec_date)
                if key not in order_cache:
                    o = Order(college_id=col.id, created_at=datetime.combine(rec_date - timedelta(days=2), time(10, 0)),
                              delivery_date=rec_date, status="delivered", exported_at=datetime.combine(rec_date - timedelta(days=2), time(10, 5)))
                    s.add(o)
                    s.flush()
                    order_cache[key] = o
                o = order_cache[key]
                qty = rng.choice([1, 1, 2, 2, 3, 4])
                s.add(OrderLine(order_id=o.id, product_id=p.id, qty=qty, unit_price=p.price))
                o.total = round(o.total + qty * p.price, 2)
                expiry = rec_date + timedelta(days=p.shelf_life_days)
                unit_type = {"chilled": "fridge", "frozen": "freezer", "dry": "dry", "ambient": "dry"}[p.storage_type]
                unit = storage[col.id][unit_type][0] if unit_type != "fridge" else rng.choice(storage[col.id]["fridge"])
                s.add(InventoryLot(college_id=col.id, product_id=p.id, storage_unit_id=unit.id, qty=qty,
                                   received_at=datetime.combine(rec_date, time(7, 30)), expiry_date=expiry, order_id=o.id,
                                   status="used" if expiry < today + timedelta(days=1) else "in_stock"))
        s.flush()

        # Demo-critical home lots: near-expiry chicken thighs (for menu suggestions) & spinach
        hf = storage[home.id]["fridge"][0]
        for sku, qty, exp_days in (("TVM-CTH05", 2, 1), ("CFP-SPI02", 1, 0), ("ISD-CRE05", 2, 2), ("CFP-MUS25", 2, 1)):
            p = products[sku]
            s.add(InventoryLot(college_id=home.id, product_id=p.id, storage_unit_id=hf.id, qty=qty,
                               received_at=now - timedelta(days=3), expiry_date=today + timedelta(days=exp_days),
                               order_id=order_cache.get((home.id, today - timedelta(days=3)), Order(id=None)).id))

        # Marketplace: other colleges' surplus stock
        market = [
            (colleges[1], "BFR-FCT10", 6, 22.0, 10, "Over-ordered for cancelled conference"),
            (colleges[2], "ISD-CRE05", 3, 9.0, 2, "Event menu changed"),
            (colleges[3], "PMB-SOU06", 5, 6.0, 1, "Surplus from Saturday brunch"),
            (colleges[4], "CFS-SAL05", 2, 30.0, 2, "Formal hall numbers dropped"),
            (colleges[1], "RDG-COC06", 4, 6.0, 120, "Recipe change"),
        ]
        for col, sku, qty, price, exp, why in market:
            p = products[sku]
            unit_type = {"chilled": "fridge", "frozen": "freezer", "dry": "dry"}[p.storage_type]
            lot = InventoryLot(college_id=col.id, product_id=p.id, storage_unit_id=storage[col.id][unit_type][0].id, qty=qty,
                               received_at=now - timedelta(days=2), expiry_date=today + timedelta(days=exp), status="listed")
            s.add(lot)
            s.flush()
            s.add(SurplusListing(college_id=col.id, kind="stock_to_colleges", lot_id=lot.id,
                                 title=f"{p.name} × {qty} packs", qty=qty, qty_remaining=qty, price=price,
                                 location=col.name, created_at=now - timedelta(hours=rng.randint(2, 30)),
                                 available_until=datetime.combine(today + timedelta(days=min(exp, 3)), time(17, 0)), status="open"))

        # One live student offer at the home college (free breakfast pastries → "free food alert")
        cro = recipes["Croissant & fruit"]
        brk = datetime.combine(today, time(10, 0))
        lst = SurplusListing(college_id=home.id, kind="meal_to_students", recipe_id=cro.id, title="Croissants & fruit from breakfast",
                             qty=14, qty_remaining=9, price=0.0, location="Buttery", created_at=brk,
                             available_until=datetime.combine(today, time(16, 0)), status="open")
        s.add(lst)
        s.flush()
        s.add(Notification(college_id=home.id, title="🆓 Free food alert",
                           body="14 croissants & fruit from breakfast, free, at the Buttery until 4pm. First come, first served.",
                           listing_id=lst.id, created_at=brk))
        for i in range(5):
            s.add(Claim(listing_id=lst.id, student_pseudo_id=students[i].pseudo_id, qty=1, amount_gbp=0.0,
                        pickup_code=f"{rng.randint(100, 999)}", created_at=brk + timedelta(minutes=10 * i)))

        # Supplier issues (home college), Cherwell is the problem child
        issue_specs = [("CFP", "short", "CFP-SPI02", "CFP-KAL02"), ("CFP", "quality", "CFP-LET01", None),
                       ("CFP", "substitution", "CFP-SPI02", "CFP-KAL02"), ("CFP", "late", None, None),
                       ("CFP", "short", "CFP-TOM06", None), ("CFP", "quality", "CFP-MUS25", None),
                       ("CFS", "late", None, None), ("CFS", "temp_breach", "CFS-SAL05", None),
                       ("TVM", "short", "TVM-CTH05", "TVM-CBR05"), ("ISD", "damaged", "ISD-EGG180", None),
                       ("PMB", "late", None, None), ("RDG", "wrong_item", "RDG-PEN06", "RDG-NOO05"),
                       ("BFR", "late", None, None)]
        notes = {"short": "Delivered less than ordered", "quality": "Wilted / poor quality on arrival",
                 "substitution": "Supplier swapped product without asking", "late": "Arrived after 10:00 cut-off",
                 "temp_breach": "Probe reading 9°C on arrival, rejected", "damaged": "Cracked trays",
                 "wrong_item": "Wrong product delivered"}
        for i in range(30):
            sc, typ, sku, sub = issue_specs[i % len(issue_specs)] if i < 13 else rng.choice(issue_specs[:6] + issue_specs[6:9])
            d = today - timedelta(days=rng.randint(1, HISTORY_DAYS))
            s.add(SupplierIssue(college_id=home.id, supplier_id=suppliers[sc].id, date=d, type=typ,
                                product_id=products[sku].id if sku else None,
                                substitute_product_id=products[sub].id if sub else None,
                                notes=notes[typ], resolved=True))
        s.add(SupplierIssue(college_id=home.id, supplier_id=suppliers["CFP"].id, date=today, type="short",
                            product_id=products["CFP-SPI02"].id, substitute_product_id=products["CFP-KAL02"].id,
                            notes="Only 1 of 3 packs of spinach delivered this morning", resolved=False))
        s.commit()
    print("Seeded OxFood demo data.")


if __name__ == "__main__":
    seed()
