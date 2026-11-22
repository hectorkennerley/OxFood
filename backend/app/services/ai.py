"""Claude (Haiku 5.5) helpers with a hard cost guard.

* Every call is cached in the AICall table by input hash: the same input is never paid for twice.
* AI_MAX_CALLS caps live calls; AI_MODE=off disables them entirely.
* Every function has a rule-based fallback, so the app works with no key at all.
"""
import hashlib
import json
import os
import re
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel
from sqlmodel import Session, func, select

from app.models import AICall

MODEL = os.getenv("AI_MODEL", "claude-haiku-5-5")
PRICE_IN, PRICE_OUT = 0.10, 0.50  # USD per million tokens (Haiku 5.5)

Stage = Literal["prep_trim", "overproduction", "servery_leftover", "plate_waste", "spoilage", "cooking_error"]


def ai_mode() -> str:
    if os.getenv("AI_MODE", "live") == "off" or not os.getenv("ANTHROPIC_API_KEY"):
        return "off"
    return "live"


def ai_status(session: Session) -> dict:
    calls = session.exec(select(func.count()).select_from(AICall)).one()
    cost = session.exec(select(func.coalesce(func.sum(AICall.cost_usd), 0.0))).one()
    return {"mode": ai_mode(), "model": MODEL, "calls": calls, "max_calls": int(os.getenv("AI_MAX_CALLS", "300")),
            "cost_usd": round(cost, 4)}


def _call(session: Session, kind: str, key_material: str, build_request, output_model: type[BaseModel]):
    """Return (parsed_dict | None, source). source is 'cache', 'ai' or 'off'."""
    h = hashlib.sha256(f"{kind}|{MODEL}|{key_material}".encode()).hexdigest()
    hit = session.exec(select(AICall).where(AICall.input_hash == h)).first()
    if hit:
        return json.loads(hit.response_json), "cache"
    if ai_mode() == "off":
        return None, "off"
    if session.exec(select(func.count()).select_from(AICall)).one() >= int(os.getenv("AI_MAX_CALLS", "300")):
        return None, "cap"
    try:
        import anthropic

        client = anthropic.Anthropic(max_retries=1, timeout=20)
        resp = client.messages.parse(model=MODEL, output_format=output_model,
                                     output_config={"effort": "low"}, **build_request())
        if resp.stop_reason in ("refusal", "max_tokens") or resp.parsed_output is None:
            return None, f"stop:{resp.stop_reason}"
        data = resp.parsed_output.model_dump()
        u = resp.usage
        cost = (u.input_tokens * PRICE_IN + u.output_tokens * PRICE_OUT) / 1_000_000
        session.add(AICall(kind=kind, input_hash=h, response_json=json.dumps(data), input_tokens=u.input_tokens,
                           output_tokens=u.output_tokens, cost_usd=cost, created_at=datetime.now()))
        session.commit()
        return data, "ai"
    except Exception as e:  # never let AI break the kitchen
        print(f"[ai] {kind} failed: {type(e).__name__}: {e}")
        return None, "error"


# ---------------------------------------------------------------- voice → waste entry
class WasteParse(BaseModel):
    dish_id: Optional[int]
    stage: Stage
    weight_kg: Optional[float]
    portions: Optional[int]
    note: str


NUM_WORDS = {"half": 0.5, "a": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
             "eight": 8, "nine": 9, "ten": 10, "twelve": 12, "fifteen": 15, "twenty": 20,
             "un": 1, "une": 1, "deux": 2, "trois": 3, "quatre": 4, "cinq": 5, "dix": 10,
             "uno": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5, "diez": 10}
STAGE_WORDS = [
    ("plate_waste", ["plate", "plates", "scraped", "assiette", "plato", "platos"]),
    ("prep_trim", ["trim", "trimming", "peel", "peeling", "épluchure", "cáscara", "recorte"]),
    ("spoilage", ["spoiled", "spoilt", "expired", "out of date", "gone off", "mouldy", "moldy", "périmé", "caducado"]),
    ("cooking_error", ["burnt", "burned", "dropped", "brûlé", "quemado"]),
    ("overproduction", ["never left", "didn't leave", "did not leave", "kitchen", "overproduc", "too much", "extra",
                        "cuisine", "cocina", "de más", "en trop"]),
    ("servery_leftover", ["servery", "counter", "leftover", "left over", "left on", "restes", "sobras", "sobrante"]),
]


def parse_waste_rules(text: str, dishes: list[dict]) -> dict:
    t = text.lower().replace(",", ".")
    weight = None
    m = re.search(r"(\d+(?:\.\d+)?)\s*(kg|kilo|kilos|kilogram|kilograms|k\b)", t)
    if m:
        weight = float(m.group(1))
    else:
        m = re.search(r"(\d+(?:\.\d+)?)\s*(g|grams|gram|gramos|grammes)\b", t)
        if m:
            weight = float(m.group(1)) / 1000
        else:
            for w, v in NUM_WORDS.items():
                if re.search(rf"\b{w}\b[\s\w]*?\b(kg|kilo|kilos|kilogram)", t):
                    weight = float(v)
                    if re.search(r"\band a half\b|\bet demi\b|\by medio\b", t):
                        weight += 0.5
                    break
    portions = None
    m = re.search(r"(\d+)\s*(portions|portion|servings|plates|raciones|porciones)", t)
    if m:
        portions = int(m.group(1))
    stage = "overproduction"
    for st, words in STAGE_WORDS:
        if any(w in t for w in words):
            stage = st
            break
    best, best_score = None, 0
    for d in dishes:
        words = [w for w in re.findall(r"[a-zà-ÿ]+", d["name"].lower()) if len(w) > 3]
        score = sum(1 for w in words if w in t or w[:-1] in t)
        if score > best_score:
            best, best_score = d["id"], score
    return {"dish_id": best, "stage": stage, "weight_kg": weight, "portions": portions, "note": text.strip()}


def parse_waste(session: Session, transcript: str, dishes: list[dict]) -> dict:
    menu = "\n".join(f"{d['id']}: {d['name']}" for d in dishes)

    def req():
        return {
            "max_tokens": 1024,
            "system": ("You turn a chef's short spoken note about food waste (English, French or Spanish) into a "
                       "structured record. Stages: prep_trim (raw trimmings), overproduction (cooked, never left the "
                       "kitchen), servery_leftover (was out on the servery), plate_waste (came back on plates), "
                       "spoilage (stock went off), cooking_error (burnt or dropped). Pick dish_id only from the menu; "
                       "use null if no dish matches. Convert grams to kg. Leave weight_kg or portions null if not said. "
                       "note: a short English summary."),
            "messages": [{"role": "user", "content": f"Today's menu:\n{menu}\n\nChef said: \"{transcript}\""}],
        }

    data, source = _call(session, "parse_waste", menu + "|" + transcript.strip().lower(), req, WasteParse)
    if data is None or (data.get("dish_id") is not None and data["dish_id"] not in {d["id"] for d in dishes}):
        data, source = parse_waste_rules(transcript, dishes), "rules"
    data["source"] = source
    return data


# ---------------------------------------------------------------- smart-bin photo → dish
class PhotoClass(BaseModel):
    dish_id: Optional[int]
    stage: Stage
    confidence: float
    description: str


def classify_photo(session: Session, image_b64: str, media_type: str, dishes: list[dict]) -> dict:
    menu = "\n".join(f"{d['id']}: {d['name']}" for d in dishes)

    def req():
        return {
            "max_tokens": 1024,
            "system": ("You are the camera on a kitchen food-waste bin. Identify which dish from today's menu is being "
                       "thrown away, and the most likely waste stage (plate_waste if it looks like scraped plates, "
                       "servery_leftover or overproduction if it's a tray or pan, prep_trim for raw peelings). "
                       "dish_id must come from the menu, or be null. confidence is 0 to 1."),
            "messages": [{"role": "user", "content": [
                {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": image_b64}},
                {"type": "text", "text": f"Today's menu:\n{menu}"},
            ]}],
        }

    data, source = _call(session, "classify_photo", menu + "|" + hashlib.sha256(image_b64.encode()).hexdigest(), req, PhotoClass)
    if data is None:
        return {"dish_id": None, "stage": "plate_waste", "confidence": 0.0,
                "description": "AI is off: pick the dish below.", "source": source}
    data["source"] = source
    return data


# ---------------------------------------------------------------- next-day menu rationale
class MenuPick(BaseModel):
    recipe_id: int
    why: str
    suggested_price: float


class MenuAdvice(BaseModel):
    summary: str
    picks: list[MenuPick]


def menu_rationale(session: Session, context: dict) -> tuple[Optional[dict], str]:
    payload = json.dumps(context, sort_keys=True, default=str)

    def req():
        return {
            "max_tokens": 2048,
            "system": ("You are a college catering planner whose goal is cutting food waste. From the ranked candidate "
                       "dishes (with the near-expiry stock and chillable leftovers each one uses up), choose up to 3 for "
                       "the meal. For each, give one short sentence on why it cuts waste, and a fair student price in £ "
                       "near its normal price. summary: one sentence for the head chef."),
            "messages": [{"role": "user", "content": payload}],
        }

    return _call(session, "menu", payload, req, MenuAdvice)
