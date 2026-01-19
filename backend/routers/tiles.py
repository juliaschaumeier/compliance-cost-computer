from __future__ import annotations

from fastapi import APIRouter

from backend.core import db
from backend.core.models import Tile, TilesResponse


router = APIRouter(prefix="/tiles", tags=["tiles"])


@router.get("", response_model=TilesResponse)
async def list_tiles() -> TilesResponse:
    tiles = db.fetch_tiles()
    return TilesResponse(tiles=tiles)


@router.post("", response_model=Tile)
async def create_tile(tile: Tile) -> Tile:
    db.upsert_tile(tile)
    return tile


@router.delete("/{tile_id}")
async def remove_tile(tile_id: str) -> dict:
    db.delete_tile(tile_id)
    return {"ok": True}


@router.post("/seed")
async def seed_tiles() -> dict:
    db.seed_from_json()
    return {"ok": True}
