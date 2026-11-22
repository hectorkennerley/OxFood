"""One live Claude call to prove the key works (costs a fraction of a cent).

    cd backend && .venv/bin/python -m app.ai_smoke
"""
import os

from sqlmodel import Session

from app.db import engine, init_db
from app.services import ai

if __name__ == "__main__":
    init_db()
    if ai.ai_mode() == "off":
        raise SystemExit("AI is off: put ANTHROPIC_API_KEY in backend/.env and make sure AI_MODE isn't 'off'.")
    dishes = [{"id": 1, "name": "Chicken tikka masala & rice"}, {"id": 2, "name": "Penne arrabbiata (vegan)"}]
    with Session(engine) as s:
        # A unique phrase so we don't just hit the cache
        r = ai.parse_waste(s, f"roughly two and a half kilos of the penne came back from the servery ({os.getpid()})", dishes)
        print("Result:", r)
        print("Status:", ai.ai_status(s))
        if r["source"] != "ai":
            raise SystemExit(f"Claude was NOT used (source={r['source']}). Check the server log above for the error.")
        print("✅ Claude Haiku is working.")
