"""Food-reuse rules engine.

Encodes simplified guidance from the FSA's Safer Food, Better Business pack.
It is decision support only: every result tells the user to verify against the
college's own HACCP plan.
"""
from dataclasses import dataclass, field

DISCLAIMER = "Guidance based on FSA Safer Food, Better Business. Always verify against your college's HACCP plan."


@dataclass
class ReuseInput:
    stage: str  # prep_trim, overproduction, servery_leftover, plate_waste, spoilage, cooking_error, unopened_stock
    left_kitchen: bool = False  # went out to a diner / was on a plate
    minutes_since_cooked: int = 30
    hot_held_63: bool = True  # held at or above 63°C the whole time
    already_reheated: bool = False
    high_risk: bool = False  # rice, seafood …
    blast_chiller: bool = False
    past_use_by: bool = False
    past_best_before: bool = False
    within_service_window: bool = True


@dataclass
class Option:
    disposition: str
    label: str
    reason: str
    recommended: bool = False
    use_within_hours: int | None = None


@dataclass
class ReuseAdvice:
    options: list[Option] = field(default_factory=list)
    blocked: list[str] = field(default_factory=list)
    disclaimer: str = DISCLAIMER


def _waste_only(advice: ReuseAdvice, reason: str) -> ReuseAdvice:
    advice.options.append(Option("compost", "Compost / anaerobic digestion", reason, recommended=True))
    return advice


def advise(i: ReuseInput) -> ReuseAdvice:
    a = ReuseAdvice()

    if i.past_use_by:
        a.blocked.append("Past its use-by date: unsafe to eat, sell or donate.")
        return _waste_only(a, "Use-by has passed, so the only safe route is disposal.")

    if i.stage == "plate_waste" or i.left_kitchen:
        a.blocked.append("Has been served to a diner: it can't be re-served.")
        return _waste_only(a, "Food that has reached a plate can't be reused. Track it to cut portion sizes instead.")

    if i.stage == "spoilage":
        a.blocked.append("Spoiled: not fit for consumption.")
        return _waste_only(a, "Spoiled stock goes to compost. OxFood will flag the lot that caused it.")

    if i.stage == "prep_trim":
        a.options.append(Option("staff_meal", "Stock, soup or staff meal",
                                "Raw trimmings (veg peel, bones) can go into stocks and soups today.", recommended=True))
        a.options.append(Option("compost", "Compost", "What can't be used goes to compost."))
        return a

    if i.stage == "unopened_stock":
        if i.past_best_before:
            a.options.append(Option("donate", "Donate (best-before passed)",
                                    "Past best-before only affects quality, so it can still be donated with judgement.", recommended=True))
        a.options.append(Option("marketplace", "List for other colleges",
                                "Unopened and in date: another college can use it before it expires.", recommended=not i.past_best_before))
        a.options.append(Option("freeze", "Freeze before use-by",
                                "If the product is freezable, freezing it before the use-by extends its life."))
        return a

    # Cooked food: overproduction (never left the kitchen) or servery leftovers
    if not i.hot_held_63 and i.minutes_since_cooked > 120:
        a.blocked.append("Held below 63°C for over 2 hours: it must be discarded.")
        return _waste_only(a, "Temperature control was lost.")

    if i.already_reheated:
        a.blocked.append("Already reheated once: it can't be chilled and reheated again.")
    if i.within_service_window:
        a.options.append(Option("offer_students", "Offer to students now",
                                "Still hot-held at ≥63°C, so it can be sold before the end of the service window.",
                                recommended=True, use_within_hours=2))

    can_chill = i.stage == "overproduction" and not i.left_kitchen and not i.already_reheated
    if can_chill and i.blast_chiller and i.minutes_since_cooked <= 90:
        hours = 24 if i.high_risk else 48
        a.options.append(Option("chill_reuse", f"Blast-chill and reuse within {hours}h",
                                f"Never left the kitchen: cool within 90 min to ≤5°C, label it, then reheat once to ≥75°C. "
                                f"{'Rice and seafood are high-risk, so the limit is 24h.' if i.high_risk else 'Use within 48h.'}",
                                recommended=not i.within_service_window, use_within_hours=hours))
    elif can_chill and not i.blast_chiller:
        a.blocked.append("No blast chiller: a large batch can't be cooled safely within 90 minutes.")
    elif can_chill and i.minutes_since_cooked > 90:
        a.blocked.append("Cooked more than 90 minutes ago: too late to chill safely.")

    if i.stage == "servery_leftover":
        a.blocked.append("Has been on the servery: don't chill it for reuse.")

    if not a.options:
        return _waste_only(a, "No safe reuse route.")
    a.options.append(Option("compost", "Compost", "If nobody claims it."))
    return a
