from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db import DB_PATH, init_db
from app.routers import analytics, core, kitchen, supply


@asynccontextmanager
async def lifespan(_: FastAPI):
    if not DB_PATH.exists():
        from app.seed import seed

        seed()
    init_db()
    yield


app = FastAPI(title="OxFood", description="Tracking every food item from distributor → kitchen → student",
              lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
for r in (core.router, kitchen.router, supply.router, analytics.router):
    app.include_router(r)


@app.get("/api/health")
def health():
    return {"ok": True}
