from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from pydantic import StringConstraints

from backend.core import db
from backend.core.session_graph import build_session_tiles_snapshot
from backend.core.models import Tile, TilesResponse


router = APIRouter(prefix="/tiles", tags=["tiles"])

AppSessionId = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=64,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$",
    ),
]
APP_SESSION_ID_QUERY_VALIDATION = Query(
    ...,
    min_length=1,
    max_length=64,
    pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$",
)


def _session_id_for_app(app_session_id: str) -> int:
    session = db.get_session_by_app_id(app_session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return int(session["session_id"])


@router.get("", response_model=TilesResponse)
async def list_tiles(
    app_session_id: str = APP_SESSION_ID_QUERY_VALIDATION
) -> TilesResponse:
    session_id = _session_id_for_app(app_session_id)
    tiles = db.fetch_tiles(session_id=session_id)
    return TilesResponse(tiles=tiles)


@router.post("", response_model=Tile)
async def create_tile(
    tile: Tile,
    app_session_id: str = APP_SESSION_ID_QUERY_VALIDATION,
) -> Tile:
    session_id = _session_id_for_app(app_session_id)
    db.upsert_tile(tile, session_id=session_id)
    return tile


@router.delete("/{tile_id}")
async def remove_tile(
    tile_id: str,
    app_session_id: str = APP_SESSION_ID_QUERY_VALIDATION,
) -> dict:
    session_id = _session_id_for_app(app_session_id)
    db.delete_tile(tile_id, session_id=session_id)
    return {"ok": True}


class RebuildTilesRequest(BaseModel):
    app_session_id: AppSessionId


@router.post("/rebuild")
async def rebuild_tiles(payload: RebuildTilesRequest) -> dict:
    session = db.get_session_by_app_id(payload.app_session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session_id = int(session["session_id"])
    tiles = build_session_tiles_snapshot(session)
    with db.transaction():
        db.clear_tiles(session_id=session_id)
        for tile in tiles:
            db.upsert_tile(tile, session_id=session_id)

    return {"ok": True}
