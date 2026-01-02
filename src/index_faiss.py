from __future__ import annotations

import json
from pathlib import Path
import sqlite3

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from .db import connect, init_schema

# Multilingual embedding modeli (yerelde cache'lenir)
EMB_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

INDEX_DIR = Path("data/index")
INDEX_PATH = INDEX_DIR / "items.faiss"
META_PATH = INDEX_DIR / "items_meta.jsonl"

def build_doc_text(row) -> str:
    # row: (item_id, receipt_id, merchant, receipt_date, name_norm, category, qty, unit, amount)
    item_id, receipt_id, merchant, date, name_norm, category, qty, unit, amount = row
    parts = [
        f"merchant: {merchant or ''}",
        f"date: {date or ''}",
        f"item: {name_norm or ''}",
        f"category: {category or ''}",
        f"qty: {qty if qty is not None else ''} {unit or ''}".strip(),
        f"amount: {amount if amount is not None else ''}",
    ]
    return " | ".join([p for p in parts if p.strip()])

def main():
    INDEX_DIR.mkdir(parents=True, exist_ok=True)

    conn = connect()
    init_schema(conn)

    rows = conn.execute(
        """
        SELECT
          i.id,
          i.receipt_id,
          r.merchant,
          r.receipt_date,
          i.name_norm,
          i.category,
          i.qty,
          i.unit,
          i.amount
        FROM items i
        JOIN receipts r ON r.id = i.receipt_id
        ORDER BY r.receipt_date, i.line_no
        """
    ).fetchall()
    conn.close()

    if not rows:
        print("NO_ITEMS")
        return

    docs = [build_doc_text(r) for r in rows]

    model = SentenceTransformer(EMB_MODEL_NAME)
    emb = model.encode(docs, normalize_embeddings=True, show_progress_bar=True)
    emb = np.asarray(emb, dtype="float32")

    dim = emb.shape[1]
    index = faiss.IndexFlatIP(dim)  # cosine similarity ~ inner product with normalized vectors
    index.add(emb)

    faiss.write_index(index, str(INDEX_PATH))

    with META_PATH.open("w", encoding="utf-8") as f:
        for r, d in zip(rows, docs):
            item_id, receipt_id, merchant, date, name_norm, category, qty, unit, amount = r
            meta = {
                "item_id": item_id,
                "receipt_id": receipt_id,
                "merchant": merchant,
                "date": date,
                "name_norm": name_norm,
                "category": category,
                "qty": qty,
                "unit": unit,
                "amount": amount,
                "doc": d,
            }
            f.write(json.dumps(meta, ensure_ascii=False) + "\n")

    print(f"INDEX_OK: items={len(rows)} dim={dim} index_path={INDEX_PATH} meta_path={META_PATH}")

if __name__ == "__main__":
    main()
