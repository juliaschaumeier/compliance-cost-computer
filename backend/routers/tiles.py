from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from backend.core import db
from backend.core.session_graph import build_session_tiles_snapshot
from backend.core.models import Tile, TilesResponse


router = APIRouter(prefix="/tiles", tags=["tiles"])


@router.get("", response_model=TilesResponse)
async def list_tiles(app_session_id: str | None = Query(default=None)) -> TilesResponse:
    session_id: int | None = None
    if app_session_id:
        session = db.get_session_by_app_id(app_session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        session_id = int(session["session_id"])
    tiles = db.fetch_tiles(session_id=session_id)
    return TilesResponse(tiles=tiles)


@router.post("", response_model=Tile)
async def create_tile(
    tile: Tile,
    app_session_id: str | None = Query(default=None),
) -> Tile:
    session_id: int | None = None
    if app_session_id:
        session = db.get_session_by_app_id(app_session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        session_id = int(session["session_id"])
    db.upsert_tile(tile, session_id=session_id)
    return tile


@router.delete("/{tile_id}")
async def remove_tile(
    tile_id: str,
    app_session_id: str | None = Query(default=None),
) -> dict:
    session_id: int | None = None
    if app_session_id:
        session = db.get_session_by_app_id(app_session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        session_id = int(session["session_id"])
    db.delete_tile(tile_id, session_id=session_id)
    return {"ok": True}


@router.post("/seed")
async def seed_tiles(app_session_id: str | None = Query(default=None)) -> dict:
    session_id: int | None = None
    if app_session_id:
        session = db.get_session_by_app_id(app_session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        session_id = int(session["session_id"])
    db.seed_from_json(session_id=session_id)
    return {"ok": True}


class RebuildTilesRequest(BaseModel):
    app_session_id: str | None = None


@router.post("/rebuild")
async def rebuild_tiles(payload: RebuildTilesRequest) -> dict:
    if payload.app_session_id:
        session = db.get_session_by_app_id(payload.app_session_id)
    else:
        session = db.get_latest_session()
    if not session:
        raise HTTPException(status_code=404, detail="No session available")

    session_id = int(session["session_id"])
    tiles = build_session_tiles_snapshot(session)
    with db.transaction():
        db.clear_tiles(session_id=session_id)
        for tile in tiles:
            db.upsert_tile(tile, session_id=session_id)

    return {"ok": True}
