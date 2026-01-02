from __future__ import annotations

import json
from pathlib import Path
import sqlite3

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from llama_cpp import Llama

from .db import connect, init_schema
from .query_parse import parse_query

EMB_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
INDEX_PATH = Path("data/index/items.faiss")
META_PATH = Path("data/index/items_meta.jsonl")

LLM_MODEL_PATH = r"models\qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf"
ANSWER_PROMPT_PATH = Path("prompts/answer_with_citations_tr.txt")


def load_meta() -> list[dict]:
    metas: list[dict] = []
    with META_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            metas.append(json.loads(line))
    return metas


def fetch_items(conn: sqlite3.Connection, item_ids: list[str]) -> list[dict]:
    if not item_ids:
        return []
    q = ",".join(["?"] * len(item_ids))
    rows = conn.execute(
        f"""
        SELECT
          i.id,
          r.receipt_date,
          r.merchant,
          r.source_path,
          i.name_raw,
          i.name_norm,
          i.category,
          i.qty,
          i.unit,
          i.amount,
          i.line_no
        FROM items i
        JOIN receipts r ON r.id = i.receipt_id
        WHERE i.id IN ({q})
        """,
        item_ids,
    ).fetchall()

    out = []
    for r in rows:
        out.append(
            {
                "item_id": r[0],
                "date": r[1],
                "merchant": r[2],
                "source_path": r[3],
                "name_raw": r[4],
                "name_norm": r[5],
                "category": r[6],
                "qty": r[7],
                "unit": r[8],
                "amount": r[9],
                "line_no": r[10],
            }
        )
    return out


def apply_filters(items: list[dict], category: str | None, date_from: str | None, date_to: str | None) -> list[dict]:
    out = items
    if category:
        out = [it for it in out if (it.get("category") == category)]
    if date_from:
        out = [it for it in out if (it.get("date") or "") >= date_from]
    if date_to:
        out = [it for it in out if (it.get("date") or "") <= date_to]
    return out


def build_results(items: list[dict]) -> dict:
    total_amount = 0.0
    count = 0
    by_category: dict[str, float] = {}
    by_merchant: dict[str, float] = {}

    for it in items:
        amt = it.get("amount")
        if isinstance(amt, (int, float)):
            total_amount += float(amt)
        count += 1

        cat = it.get("category") or "diger"
        by_category[cat] = by_category.get(cat, 0.0) + (float(amt) if isinstance(amt, (int, float)) else 0.0)

        m = it.get("merchant") or "UNKNOWN"
        by_merchant[m] = by_merchant.get(m, 0.0) + (float(amt) if isinstance(amt, (int, float)) else 0.0)

    return {
        "matched_item_count": count,
        "matched_total_amount_try": round(total_amount, 2),
        "by_category_try": {k: round(v, 2) for k, v in sorted(by_category.items(), key=lambda x: -x[1])},
        "by_merchant_try": {k: round(v, 2) for k, v in sorted(by_merchant.items(), key=lambda x: -x[1])},
    }


def format_evidence(items_sorted: list[dict], limit: int = 5) -> str:
    lines = []
    for it in items_sorted[:limit]:
        qty = it.get("qty")
        unit = it.get("unit") or ""
        amt = it.get("amount")
        lines.append(
            f"- {it.get('date')} | {it.get('merchant')} | {it.get('name_raw')} "
            f"(qty={qty} {unit}".strip()
            + f", amount={amt}) | source: {it.get('source_path')}"
        )
    return "\n".join(lines)


def build_prompt(question: str, results: dict, evidence: str) -> str:
    tpl = ANSWER_PROMPT_PATH.read_text(encoding="utf-8")
    return (
        tpl.replace("{{QUESTION}}", question.strip())
        .replace("{{RESULTS}}", json.dumps(results, ensure_ascii=False, indent=2))
        .replace("{{EVIDENCE}}", evidence.strip() if evidence.strip() else "YOK")
    )


def main():
    question = input("Soru: ").strip()
    if not question:
        print("EMPTY_QUESTION")
        return

    spec = parse_query(question)

    if not INDEX_PATH.exists() or not META_PATH.exists():
        print("MISSING_INDEX: Önce Adım 6 (index_faiss) tamamlanmalı.")
        return

    metas = load_meta()
    conn = connect()
    init_schema(conn)

    # Eğer ürün terimi yok ama sadece kategori/tarih toplam sorusuysa:
    # retrieval yerine DB'den filtreli çekip hesaplamak daha doğru.
    if spec.product_term is None and (spec.category or spec.date_from or spec.date_to):
        rows = conn.execute(
            """
            SELECT
              i.id,
              r.receipt_date,
              r.merchant,
              r.source_path,
              i.name_raw,
              i.name_norm,
              i.category,
              i.qty,
              i.unit,
              i.amount,
              i.line_no
            FROM items i
            JOIN receipts r ON r.id = i.receipt_id
            """
        ).fetchall()
        items = [
            {
                "item_id": r[0],
                "date": r[1],
                "merchant": r[2],
                "source_path": r[3],
                "name_raw": r[4],
                "name_norm": r[5],
                "category": r[6],
                "qty": r[7],
                "unit": r[8],
                "amount": r[9],
                "line_no": r[10],
            }
            for r in rows
        ]
        items_f = apply_filters(items, spec.category, spec.date_from, spec.date_to)
        conn.close()

        if not items_f:
            print("Bu soruya yanıt verecek kayıt bulamadım.")
            return

        # Kanıt için en pahalıları göster
        items_sorted = sorted(items_f, key=lambda it: float(it["amount"] or 0.0), reverse=True)
        results = build_results(items_f)
        evidence = format_evidence(items_sorted, limit=5)

    else:
        # Retrieval yolu (ürün araması veya genel soru)
        index = faiss.read_index(str(INDEX_PATH))
        emb_model = SentenceTransformer(EMB_MODEL_NAME)

        q_text = spec.product_term if spec.product_term else question
        qv = emb_model.encode([q_text], normalize_embeddings=True)
        qv = np.asarray(qv, dtype="float32")

        top_k = min(25, len(metas))
        D, I = index.search(qv, top_k)
        idxs = [int(x) for x in I[0] if int(x) >= 0]
        item_ids = [metas[i]["item_id"] for i in idxs]

        items = fetch_items(conn, item_ids)
        conn.close()

        # similarity score map
        score_map = {metas[i]["item_id"]: float(D[0][pos]) for pos, i in enumerate(idxs)}
        items_sorted = sorted(items, key=lambda it: score_map.get(it["item_id"], -1.0), reverse=True)

        # filtre uygula (kategori/tarih)
        items_sorted = apply_filters(items_sorted, spec.category, spec.date_from, spec.date_to)

        if not items_sorted:
            print("Bu soruya yanıt verecek kayıt bulamadım.")
            return

        results = build_results(items_sorted)
        evidence = format_evidence(items_sorted, limit=5)

    # LLM ile anlatım
    llm = Llama(
        model_path=LLM_MODEL_PATH,
        n_ctx=2048,
        n_threads=8,
        verbose=False,
    )

    prompt = build_prompt(question, results, evidence)
    out = llm(prompt, max_tokens=300, temperature=0, top_p=1.0, stop=["<|im_end|>"])
    answer = out["choices"][0]["text"].strip()

    print("\n" + answer + "\n")


if __name__ == "__main__":
    main()
