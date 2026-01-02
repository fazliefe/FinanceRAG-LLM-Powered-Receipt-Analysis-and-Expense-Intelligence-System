from __future__ import annotations

import sqlite3
from .db import connect, init_schema
from .normalize import normalize_name
from .categorize import categorize

def main():
    conn = connect()
    init_schema(conn)

    rows = conn.execute("SELECT id, name_raw FROM items").fetchall()
    if not rows:
        print("NO_ITEMS")
        return

    updated = 0
    for item_id, name_raw in rows:
        norm = normalize_name(name_raw)
        cat = categorize(norm)
        conn.execute(
            "UPDATE items SET name_norm = ?, category = ? WHERE id = ?",
            (norm, cat, item_id),
        )
        updated += 1

    conn.commit()

    counts = conn.execute(
        "SELECT category, COUNT(*) FROM items GROUP BY category ORDER BY COUNT(*) DESC"
    ).fetchall()
    conn.close()

    print(f"ENRICH_OK: updated={updated} categories={counts}")

if __name__ == "__main__":
    main()
