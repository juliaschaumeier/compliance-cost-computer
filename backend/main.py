from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.core import db
from backend.routers import (
    models,
    regulations,
    tiles,
    sessions,
    processes,
    case_groups,
    process_steps,
    effort,
    costs,
)


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    db.ensure_db()


app.include_router(tiles.router)
app.include_router(models.router)
app.include_router(regulations.router)
app.include_router(processes.router)
app.include_router(case_groups.router)
app.include_router(process_steps.router)
app.include_router(effort.router)
app.include_router(costs.router)
app.include_router(sessions.router)


@app.get("/")
async def root() -> dict:
    return {"message": "CCC backend API"}


@app.get("/health")
async def health_check() -> dict:
    return {"status": "healthy"}

