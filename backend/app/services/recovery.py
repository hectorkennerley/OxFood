"""Rule table: supplier or kitchen problem → concrete recovery steps."""

SUPPLIER_RECOVERY = {
    "short": [
        "Use the substitute product if one was sent, or order it from an alternative active supplier.",
        "Re-plan portions: switch tomorrow's dish to one that uses stock already in date.",
        "Ask a nearby college on the marketplace for the missing item.",
    ],
    "late": [
        "Swap the first service's dish to one cooked from stock already on site.",
        "Move prep of the affected dish later in the day, and tell the head chef.",
        "If late deliveries keep happening, move the order cut-off earlier or switch supplier.",
    ],
    "quality": [
        "Reject and photograph the product, and claim a credit.",
        "Trim and use any usable portion today (soups, sauces) rather than binning all of it.",
        "Raise it at the next supplier review: this supplier's quality-issue rate is tracked.",
    ],
    "substitution": [
        "Check allergens on the substitute before using it.",
        "Update the recipe for this service so costs and waste are tracked correctly.",
        "Tell the supplier which substitutes are acceptable for next time.",
    ],
    "temp_breach": [
        "Reject the delivery: chilled food arriving above 8°C is unsafe.",
        "Record the probe reading for your HACCP log.",
        "Re-order from an alternative supplier or use frozen stock.",
    ],
    "damaged": [
        "Separate undamaged stock and use it first.",
        "Photograph the damage and claim a credit.",
    ],
    "wrong_item": [
        "Check if the wrong item can be used elsewhere on this week's menu before returning it.",
        "Re-order the correct item and adjust the menu if needed.",
    ],
}

KITCHEN_RECOVERY = {
    "overproduction": "Next time, cook to OxFood's recommended portions and batch-cook the second half during service.",
    "servery_leftover": "Hold back part of the batch in the kitchen, so leftovers stay reusable and never reach the servery.",
    "plate_waste": "Plate waste for this dish is high: try a smaller default portion with free seconds.",
    "spoilage": "Use first-expiry-first-out: OxFood's expiry alerts flag this stock 48h earlier.",
    "prep_trim": "Use trimmings in stocks and soups, and check whether a pre-prepped product would waste less.",
}
