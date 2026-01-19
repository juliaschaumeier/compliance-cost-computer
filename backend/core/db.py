from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Iterable, List

from .config import settings
from .models import Tile


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def get_conn() -> sqlite3.Connection:
    _ensure_parent(settings.db_path)
    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS tiles (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            text TEXT NOT NULL,
            meta JSON,
            col INTEGER DEFAULT 0,
            row INTEGER DEFAULT 0,
            deletable INTEGER DEFAULT 1
        );
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS links (
            source TEXT NOT NULL,
            target TEXT NOT NULL,
            PRIMARY KEY (source, target),
            FOREIGN KEY (source) REFERENCES tiles(id) ON DELETE CASCADE,
            FOREIGN KEY (target) REFERENCES tiles(id) ON DELETE CASCADE
        );
        """
    )
    conn.commit()
    conn.close()


def seed_from_json() -> None:
    if not settings.seed_json.exists():
        return
    data = json.loads(settings.seed_json.read_text(encoding="utf-8"))
    tiles = data.get("tiles", [])
    links = []
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM links")
    cur.execute("DELETE FROM tiles")
    for tile in tiles:
        tile_id = tile["id"]
        cur.execute(
            """
            INSERT OR REPLACE INTO tiles (id, title, text, meta, col, row, deletable)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                tile_id,
                tile.get("title", tile_id),
                tile.get("text", ""),
                json.dumps(tile.get("meta_information", {}), ensure_ascii=False),
                tile.get("column", 0),
                tile.get("row", 0),
                1 if tile.get("deletable", True) else 0,
            ),
        )
        for src in tile.get("link_from_tile", []):
            links.append((src, tile_id))
    for src, tgt in links:
        cur.execute(
            """
            INSERT OR REPLACE INTO links (source, target)
            VALUES (?, ?)
            """,
            (src, tgt),
        )
    conn.commit()
    conn.close()


def ensure_db() -> None:
    init_db()
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) as c FROM tiles")
    if cur.fetchone()["c"] == 0:
        seed_from_json()
    conn.close()


def fetch_tiles() -> List[Tile]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM tiles")
    tiles: List[Tile] = []
    for row in cur.fetchall():
        tile_id = row["id"]
        cur_links = conn.execute("SELECT source FROM links WHERE target = ?", (tile_id,)).fetchall()
        tiles.append(
            Tile(
                id=tile_id,
                title=row["title"],
                text=row["text"],
                meta_information=json.loads(row["meta"] or "{}"),
                column=row["col"],
                row=row["row"],
                deletable=bool(row["deletable"]),
                link_from_tile=[r["source"] for r in cur_links],
            )
        )
    conn.close()
    return tiles


def upsert_tile(tile: Tile) -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT OR REPLACE INTO tiles (id, title, text, meta, col, row, deletable)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            tile.id,
            tile.title,
            tile.text,
            json.dumps(tile.meta_information or {}, ensure_ascii=False),
            tile.column,
            tile.row,
            1 if tile.deletable else 0,
        ),
    )
    conn.commit()
    conn.close()
    if tile.link_from_tile is not None:
        set_links(tile.id, tile.link_from_tile)


def delete_tile(tile_id: str) -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM links WHERE target = ? OR source = ?", (tile_id, tile_id))
    cur.execute("DELETE FROM tiles WHERE id = ?", (tile_id,))
    conn.commit()
    conn.close()


def set_links(target_id: str, sources: Iterable[str]) -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM links WHERE target = ?", (target_id,))
    for src in sources:
        cur.execute(
            "INSERT OR REPLACE INTO links (source, target) VALUES (?, ?)",
            (src, target_id),
        )
    conn.commit()
    conn.close()
