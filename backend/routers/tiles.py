from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from pydantic import StringConstraints

from backend.core import db
from backend.core.session_graph import (
    build_session_tiles_snapshot,
    persist_session_tiles_snapshot,
)
from backend.core.models import Tile, TilesResponse
from backend.core.norm_addressees import ADMINISTRATION, normalize_norm_addressee


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


def _is_step_tile_stale(tile: Tile) -> bool:
    if not tile.id.startswith("step_"):
        return False
    meta = tile.meta_information or {}
    if not isinstance(meta.get("time_required_current"), dict) or not isinstance(
        meta.get("time_required_proposed"), dict
    ):
        return True
    return False


def _is_case_group_tile_stale(tile: Tile) -> bool:
    if not tile.id.startswith("case_group_"):
        return False
    meta = tile.meta_information or {}
    required_keys = (
        "addressees_current",
        "annual_frequency_current",
        "cases_current",
        "addressees_proposed",
        "annual_frequency_proposed",
        "cases_proposed",
    )
    if any(key not in meta for key in required_keys):
        return True
    return False


def _tiles_need_structured_rebuild(tiles: list[Tile]) -> bool:
    return any(_is_step_tile_stale(tile) or _is_case_group_tile_stale(tile) for tile in tiles)


def _tiles_need_empty_state_rebuild(
    tiles: list[Tile],
    *,
    session_id: int,
    norm_addressee: str,
) -> bool:
    if norm_addressee == ADMINISTRATION:
        return False
    tile_ids = {tile.id for tile in tiles}
    if "empty_addressee" in tile_ids:
        return False
    if tile_ids != {"law_tile"}:
        return False
    has_any_structure = bool(
        db.list_regulations_for_session_and_addressee(session_id, norm_addressee)
        or db.list_processes_for_session_and_addressee(session_id, norm_addressee)
        or db.list_case_groups_for_session_and_addressee(session_id, norm_addressee)
        or db.list_process_steps_for_session_and_addressee(session_id, norm_addressee)
    )
    return not has_any_structure


def _tiles_need_missing_structure_rebuild(
    session: dict,
    tiles: list[Tile],
    *,
    norm_addressee: str,
) -> bool:
    expected_tiles = build_session_tiles_snapshot(session, norm_addressee)
    expected_ids = {tile.id for tile in expected_tiles}
    current_ids = {tile.id for tile in tiles}
    if expected_ids == current_ids:
        return False
    # Only rebuild when persisted domain structure implies that tiles should exist.
    # This restores deleted derived tiles from the underlying DB state.
    return expected_ids.issuperset(current_ids) and bool(expected_ids - current_ids)


def _rebuild_tiles_for_session(
    session: dict,
    norm_addressee: str = ADMINISTRATION,
) -> None:
    session_id = int(session["session_id"])
    resolved = normalize_norm_addressee(norm_addressee)
    tiles = build_session_tiles_snapshot(session, resolved)
    with db.transaction():
        db.clear_tiles(session_id=session_id, norm_addressee=resolved)
        for tile in tiles:
            db.upsert_tile(tile, session_id=session_id, norm_addressee=resolved)


@router.get("", response_model=TilesResponse)
async def list_tiles(
    app_session_id: str = APP_SESSION_ID_QUERY_VALIDATION,
    norm_addressee: str | None = Query(default=None),
) -> TilesResponse:
    session = db.get_session_by_app_id(app_session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session_id = int(session["session_id"])
    resolved = normalize_norm_addressee(norm_addressee)
    tiles = db.fetch_tiles(session_id=session_id, norm_addressee=resolved)
    if not tiles:
        has_process_steps = bool(
            db.list_process_steps_for_session_and_addressee(session_id, resolved)
        )
        has_case_groups = bool(
            db.list_case_groups_for_session_and_addressee(session_id, resolved)
        )
        has_processes = bool(
            db.list_processes_for_session_and_addressee(session_id, resolved)
        )
        has_regulations = bool(
            db.list_regulations_for_session_and_addressee(session_id, resolved)
        )
        if (
            session.get("law_diff_title")
            or session.get("law_diff_blurb")
            or session.get("law_diff_summary")
            or has_regulations
            or has_processes
            or has_case_groups
            or has_process_steps
        ):
            tiles = persist_session_tiles_snapshot(session, resolved)
    elif _tiles_need_structured_rebuild(tiles) or _tiles_need_empty_state_rebuild(
        tiles,
        session_id=session_id,
        norm_addressee=resolved,
    ) or _tiles_need_missing_structure_rebuild(
        session,
        tiles,
        norm_addressee=resolved,
    ):
        has_process_steps = bool(
            db.list_process_steps_for_session_and_addressee(session_id, resolved)
        )
        has_case_groups = bool(
            db.list_case_groups_for_session_and_addressee(session_id, resolved)
        )
        if has_process_steps or has_case_groups or resolved != ADMINISTRATION:
            _rebuild_tiles_for_session(session, resolved)
            tiles = db.fetch_tiles(session_id=session_id, norm_addressee=resolved)
    return TilesResponse(tiles=tiles)


@router.post("", response_model=Tile)
async def create_tile(
    tile: Tile,
    app_session_id: str = APP_SESSION_ID_QUERY_VALIDATION,
    norm_addressee: str | None = Query(default=None),
) -> Tile:
    session_id = _session_id_for_app(app_session_id)
    resolved = normalize_norm_addressee(norm_addressee)
    db.upsert_tile(tile, session_id=session_id, norm_addressee=resolved)
    return tile


@router.delete("/{tile_id}")
async def remove_tile(
    tile_id: str,
    app_session_id: str = APP_SESSION_ID_QUERY_VALIDATION,
    norm_addressee: str | None = Query(default=None),
) -> dict:
    session_id = _session_id_for_app(app_session_id)
    resolved = normalize_norm_addressee(norm_addressee)
    db.delete_tile(tile_id, session_id=session_id, norm_addressee=resolved)
    return {"ok": True}


class RebuildTilesRequest(BaseModel):
    app_session_id: AppSessionId
    norm_addressee: str | None = None


@router.post("/rebuild")
async def rebuild_tiles(payload: RebuildTilesRequest) -> dict:
    session = db.get_session_by_app_id(payload.app_session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    resolved = normalize_norm_addressee(payload.norm_addressee)
    _rebuild_tiles_for_session(session, resolved)

    return {"ok": True}
