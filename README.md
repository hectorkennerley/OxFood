# 🌱 OxFood

A platform to reduce food waste across Oxford colleges by tracking every food item from **distributor → kitchen → student**.

The full plan is in [`docs/PLAN.md`](docs/PLAN.md) (PDF: [`docs/OxFood-Hackathon-Plan.pdf`](docs/OxFood-Hackathon-Plan.pdf)).

## Run it

```bash
./dev.sh            # starts API (:8000) + web app (:5173)
./dev.sh --reset    # same, but regenerates the demo data first
```

The first run sets everything up: a Python venv in `backend/.venv` and, if Node isn't installed, a local Node in `frontend/.node`. It needs Python 3.11+ and [`uv`](https://docs.astral.sh/uv/) (or plain `pip`).

| Window | URL |
|---|---|
| Manager dashboard | http://localhost:5173/ |
| Kitchen tablet | http://localhost:5173/tablet |
| Smart bin (camera + scale) | http://localhost:5173/bin |
| Student phone | http://localhost:5173/student |
| API docs | http://localhost:8000/docs |

Voice input uses the browser's speech recognition: use **Chrome**. You can always type the sentence instead.

## AI (optional, Claude Haiku 5.5)

Everything works without a key, using rule-based fallbacks. To turn Claude on:

```bash
cp backend/.env.example backend/.env    # then paste your key into ANTHROPIC_API_KEY
cd backend && .venv/bin/python -m app.ai_smoke
```

Cost guard: every response is cached, `AI_MAX_CALLS` caps paid calls, and `AI_MODE=off` disables them. Set a spend limit in the Anthropic Console too. Never commit `backend/.env`.

## Tests

```bash
cd backend && .venv/bin/python -m pytest -q
```

## Demo script (≈3 min, three windows)

1. **Dashboard:** waste per cover has fallen every week since go-live. Under "Tonight", OxFood says to cook fewer portions than were booked.
2. **Order:** click "Build suggested order", then "Place order". The Foodbuy CSV downloads. **Suppliers:** today's open spinach short-delivery comes with recovery steps.
3. **Tablet:** type or say *"about three kilos of chicken tikka never left the kitchen"*, then Save. The safety advice appears. Tap "Send offer".
4. **Student window:** the alert pops up. Tap "Reserve" to get a pickup code.
5. **Marketplace:** buy Keble's frozen chicken thighs (the "fits your freezer" check runs first). Then click "see its journey".
6. **Dashboard:** the numbers have moved. End on the business model slide.

Reset between rehearsals with `./dev.sh --reset`, or `curl -X POST localhost:8000/api/admin/reset`.

## Structure

```
backend/app/models.py        ontology: object types (tables) + link types (foreign keys)
backend/app/seed.py          fabricated demo data, generated relative to today
backend/app/routers/         actions (POST) and views (GET)
backend/app/services/        safety rules, forecast, ordering, storage, recovery, Foodbuy CSV, AI
frontend/src/routes/         one file per page
frontend/src/i18n/           EN / FR / ES strings for the kitchen tablet
```

All data is simulated. Supplier names are fictional.
