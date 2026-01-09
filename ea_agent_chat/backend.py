import json
import sqlite3
from pathlib import Path
from flask import Flask, jsonify, request, abort

DB_PATH = Path(__file__).with_name("tiles.db")
SEED_JSON = Path(__file__).with_name("mockup_data.json")

app = Flask(__name__)


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
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


def seed_from_json():
    if not SEED_JSON.exists():
        return
    data = json.loads(SEED_JSON.read_text(encoding="utf-8"))
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


@app.route("/tiles", methods=["GET"])
def list_tiles():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM tiles")
    tiles = []
    for row in cur.fetchall():
        tile_id = row["id"]
        cur_links = conn.execute("SELECT source FROM links WHERE target = ?", (tile_id,)).fetchall()
        tiles.append(
            {
                "id": tile_id,
                "title": row["title"],
                "text": row["text"],
                "meta_information": json.loads(row["meta"] or "{}"),
                "column": row["col"],
                "row": row["row"],
                "deletable": bool(row["deletable"]),
                "link_from_tile": [r["source"] for r in cur_links],
            }
        )
    conn.close()
    return jsonify({"tiles": tiles})


@app.route("/tiles", methods=["POST"])
def create_tile():
    body = request.get_json(force=True, silent=True) or {}
    required = ["id", "title", "text"]
    if not all(k in body for k in required):
        abort(400, "id, title, text are required")
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT OR REPLACE INTO tiles (id, title, text, meta, col, row, deletable)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            body["id"],
            body["title"],
            body.get("text", ""),
            json.dumps(body.get("meta_information", {}), ensure_ascii=False),
            body.get("column", 0),
            body.get("row", 0),
            1 if body.get("deletable", True) else 0,
        ),
    )
    conn.commit()
    conn.close()
    if "link_from_tile" in body:
        set_links(body["id"], body.get("link_from_tile", []))
    return jsonify({"ok": True, "id": body["id"]})


@app.route("/tiles/<tile_id>", methods=["DELETE"])
def delete_tile(tile_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM links WHERE target = ? OR source = ?", (tile_id, tile_id))
    cur.execute("DELETE FROM tiles WHERE id = ?", (tile_id,))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


def set_links(target_id, sources):
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


def ensure_db():
    init_db()
    # Only seed if DB is empty
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) as c FROM tiles")
    if cur.fetchone()["c"] == 0:
        seed_from_json()
    conn.close()


if __name__ == "__main__":
    ensure_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
