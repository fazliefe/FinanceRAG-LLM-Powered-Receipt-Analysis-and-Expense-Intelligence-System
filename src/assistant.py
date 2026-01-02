from __future__ import annotations

import csv
import json
import re
from pathlib import Path
import sqlite3

import faiss
import numpy as np
from llama_cpp import Llama
from sentence_transformers import SentenceTransformer

from .db import connect, init_schema
from .query_parse import parse_query
from .normalize import normalize_name

# ====== LLM ======
LLM_MODEL_PATH = r"models\qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf"
_CACHED_LLM = None

def get_llm():
    global _CACHED_LLM
    if _CACHED_LLM is None:
        # Daha hızlı yükleme için n_gpu_layers=-1 (varsa GPU) veya n_threads
        _CACHED_LLM = Llama(model_path=LLM_MODEL_PATH, n_ctx=2048, n_threads=8, verbose=False)
    return _CACHED_LLM

# ====== RAG index ======
EMB_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
_CACHED_EMB_MODEL = None

def get_emb_model():
    global _CACHED_EMB_MODEL
    if _CACHED_EMB_MODEL is None:
        _CACHED_EMB_MODEL = SentenceTransformer(EMB_MODEL_NAME)
    return _CACHED_EMB_MODEL
INDEX_PATH = Path("data/index/items.faiss")
META_PATH = Path("data/index/items_meta.jsonl")

# ====== Reports ======
REPORT_DIR = Path("data/reports")
P_MONTHLY_TOTAL = REPORT_DIR / "monthly_total.csv"
P_MONTHLY_CAT = REPORT_DIR / "monthly_by_category.csv"
P_TOP_ITEMS = REPORT_DIR / "top_items_by_month_top20.csv"

# ====== Prompts ======
ANSWER_PROMPT_RAG = Path("prompts/answer_with_citations_tr.txt")

PROMPT_REPORTS = """<|im_start|>system
Sen, kişisel harcama raporlarını açıklayan bir asistansın.
Sana "RAPOR_VERISI" verilecek.

Kurallar:
- Sadece RAPOR_VERISI'ne dayan.
- Hesap yapma; sayılar zaten rapordan geliyor.
- Cevap kısa ve net olsun.
- Eğer kullanıcı bir ay belirtmişse, o aya odaklan.
- Eğer ay belirtilmemişse mevcut ayları listele ve ay sor (tek cümleyle).

<|im_end|>
<|im_start|>user
SORU:
{question}

RAPOR_VERISI:
{report_data}
<|im_end|>
<|im_start|>assistant
"""


# ===================== Router / Intent =====================
def is_report_question(q: str) -> bool:
    x = (q or "").lower()
    has_month = re.search(r"(20\d{2})[-/](\d{1,2})", x) is not None
    wants_distribution = any(k in x for k in ["kategorilere", "dağılım", "dagilim", "kırılım", "kirilim"])
    wants_top = any(k in x for k in ["en çok", "en cok", "top", "ilk 3", "ilk üç", "ilk3"])
    wants_monthly_total = ("toplam" in x) and (has_month or "ay" in x)
    return has_month and (wants_distribution or wants_top or wants_monthly_total)

def is_times_question(q: str) -> bool:
    x = (q or "").lower()
    return any(k in x for k in ["kaç kez", "kac kez", "kaç defa", "kac defa"])

def is_qty_question(q: str) -> bool:
    x = (q or "").lower()
    return any(k in x for k in ["kaç adet", "kac adet", "kaç tane", "kac tane"])

def is_liters_question(q: str) -> bool:
    x = (q or "").lower()
    return "kaç litre" in x or "kac litre" in x or "litre" in x


# ===================== Volume helpers (for liters) =====================
def parse_volume_liters(name_norm: str) -> float | None:
    """
    Örn:
      'su 1.5l' -> 1.5
      'su 0.5lt' -> 0.5
      'su 19l damacana' -> 19
    """
    if not name_norm:
        return None
    x = name_norm.lower().replace("lt", "l")
    m = re.search(r"(\d+(?:\.\d+)?)\s*l\b", x)
    if not m:
        return None
    try:
        return float(m.group(1))
    except:
        return None

def compute_volume_stats(items: list[dict]) -> tuple[float | None, dict[str, float]]:
    """
    total_liters_est: qty * litre
    breakdown_units: {'0.5l': 12, '1.5l': 12, '19l': 1} gibi
    """
    total_liters = 0.0
    any_liters = False
    breakdown: dict[str, float] = {}

    for it in items:
        qty = it.get("qty")
        if not isinstance(qty, (int, float)):
            continue

        liters_each = parse_volume_liters(it.get("name_norm") or "")
        if liters_each is None:
            continue

        any_liters = True
        total_liters += float(qty) * liters_each

        key = f"{liters_each:g}l"
        breakdown[key] = breakdown.get(key, 0.0) + float(qty)

    return (round(total_liters, 3) if any_liters else None, breakdown)


# ===================== REPORT ENGINE =====================
def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def pick_month(question: str) -> str | None:
    m = re.search(r"(20\d{2})[-/](\d{1,2})", question)
    if not m:
        return None
    y = m.group(1)
    mo = int(m.group(2))
    return f"{y}-{mo:02d}"

def answer_from_reports(question: str) -> str:
    monthly_total = read_csv(P_MONTHLY_TOTAL)
    monthly_cat = read_csv(P_MONTHLY_CAT)
    top_items = read_csv(P_TOP_ITEMS)

    months = sorted({r.get("month") for r in monthly_total if r.get("month")})
    target_month = pick_month(question)

    report = {"available_months": months}
    if target_month:
        report["target_month"] = target_month
        report["monthly_total"] = [r for r in monthly_total if r.get("month") == target_month]
        report["monthly_by_category"] = [r for r in monthly_cat if r.get("month") == target_month]
        report["top_items_top10"] = [r for r in top_items if r.get("month") == target_month][:10]
    else:
        report["note"] = "Soru içinde ay (YYYY-MM) belirtilmedi."

    llm = get_llm()
    prompt = PROMPT_REPORTS.format(question=question, report_data=report)
    out = llm(prompt, max_tokens=250, temperature=0, top_p=1.0, stop=["<|im_end|>"])
    return out["choices"][0]["text"].strip()


# ===================== RAG ENGINE =====================
def load_meta() -> list[dict]:
    metas: list[dict] = []
    with META_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            metas.append(json.loads(line))
    return metas

def fetch_items_by_ids(conn: sqlite3.Connection, item_ids: list[str]) -> list[dict]:
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

def db_find_by_term(conn: sqlite3.Connection, term_norm: str) -> list[dict]:
    # "su" gibi kısa terimde %su% = "sut" gibi yanlış eşleşme riski.
    if term_norm == "su":
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
            WHERE
              i.name_norm = 'su'
              OR i.name_norm LIKE 'su %'
              OR i.name_norm LIKE '% su %'
              OR i.name_norm LIKE '% su'
            """
        ).fetchall()
    else:
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
            WHERE i.name_norm LIKE ?
            """,
            (f"%{term_norm}%",),
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
    total_qty = 0.0
    qty_any = False

    by_category: dict[str, float] = {}
    by_merchant: dict[str, float] = {}

    for it in items:
        amt = it.get("amount")
        if isinstance(amt, (int, float)):
            total_amount += float(amt)

        q = it.get("qty")
        if isinstance(q, (int, float)):
            total_qty += float(q)
            qty_any = True

        count += 1

        cat = it.get("category") or "diger"
        by_category[cat] = by_category.get(cat, 0.0) + (float(amt) if isinstance(amt, (int, float)) else 0.0)

        m = it.get("merchant") or "UNKNOWN"
        by_merchant[m] = by_merchant.get(m, 0.0) + (float(amt) if isinstance(amt, (int, float)) else 0.0)

    total_liters_est, volume_breakdown_units = compute_volume_stats(items)

    return {
        "matched_item_count": count,
        "matched_total_amount_try": round(total_amount, 2),
        "total_qty": round(total_qty, 3) if qty_any else None,
        "times_purchased": count,
        "total_liters_est": total_liters_est,
        "volume_breakdown_units": volume_breakdown_units,
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

def build_prompt_rag(question: str, results: dict, evidence: str) -> str:
    tpl = ANSWER_PROMPT_RAG.read_text(encoding="utf-8")
    return (
        tpl.replace("{{QUESTION}}", question.strip())
        .replace("{{RESULTS}}", json.dumps(results, ensure_ascii=False, indent=2))
        .replace("{{EVIDENCE}}", evidence.strip() if evidence.strip() else "YOK")
    )

def _format_breakdown_line(bd: dict[str, float]) -> str:
    # '0.5l': 12, '1.5l': 12 ... -> "0.5l: 12 adet, 1.5l: 12 adet"
    def key_to_float(k: str) -> float:
        try:
            return float(k.replace("l", ""))
        except:
            return 1e9

    parts = []
    for k, v in sorted(bd.items(), key=lambda x: key_to_float(x[0])):
        vv = int(v) if float(v).is_integer() else v
        parts.append(f"{k}: {vv} adet")
    return ", ".join(parts)

def answer_from_rag(question: str) -> str:
    if not INDEX_PATH.exists() or not META_PATH.exists():
        return "RAG index bulunamadı. Önce indeksleme (Adım 6) tamamlanmalı."

    metas = load_meta()
    spec = parse_query(question)

    conn = connect()
    init_schema(conn)

    # 1) "kaç kez/kaç adet/kaç litre" -> deterministik DB LIKE + filtre
    if spec.product_term and (is_times_question(question) or is_qty_question(question) or is_liters_question(question)):
        term_norm = normalize_name(spec.product_term)
        items = db_find_by_term(conn, term_norm)
        items = apply_filters(items, spec.category, spec.date_from, spec.date_to)
        conn.close()

        if not items:
            return "Bu soruya yanıt verecek kayıt bulamadım."

        items_sorted = sorted(items, key=lambda it: (it.get("date") or ""), reverse=True)

        results = build_results(items)
        evidence = format_evidence(items_sorted, limit=5)

        llm = get_llm()
        prompt = build_prompt_rag(question, results, evidence)
        out = llm(prompt, max_tokens=300, temperature=0, top_p=1.0, stop=["<|im_end|>"])
        text = out["choices"][0]["text"].strip()

        # Adım 17: litre sorularında kırılımı deterministik ekle
        if is_liters_question(question):
            bd = results.get("volume_breakdown_units") or {}
            if bd:
                text += "\n\nKırılım: " + _format_breakdown_line(bd)

        return text

    # 2) Sadece kategori/tarih toplam soruları -> DB üzerinden hesap
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
            return "Bu soruya yanıt verecek kayıt bulamadım."

        items_sorted = sorted(items_f, key=lambda it: float(it.get("amount") or 0.0), reverse=True)
        results = build_results(items_f)
        evidence = format_evidence(items_sorted, limit=5)

        llm = get_llm()
        prompt = build_prompt_rag(question, results, evidence)
        out = llm(prompt, max_tokens=300, temperature=0, top_p=1.0, stop=["<|im_end|>"])
        return out["choices"][0]["text"].strip()

    # 3) Retrieval yolu
    index = faiss.read_index(str(INDEX_PATH))
    emb_model = get_emb_model()

    q_text = spec.product_term if spec.product_term else question
    qv = emb_model.encode([q_text], normalize_embeddings=True)
    qv = np.asarray(qv, dtype="float32")

    top_k = min(25, len(metas))
    D, I = index.search(qv, top_k)
    idxs = [int(x) for x in I[0] if int(x) >= 0]
    item_ids = [metas[i]["item_id"] for i in idxs]

    items = fetch_items_by_ids(conn, item_ids)
    conn.close()

    score_map = {metas[i]["item_id"]: float(D[0][pos]) for pos, i in enumerate(idxs)}
    items_sorted = sorted(items, key=lambda it: score_map.get(it["item_id"], -1.0), reverse=True)
    items_sorted = apply_filters(items_sorted, spec.category, spec.date_from, spec.date_to)

    if not items_sorted:
        return "Bu soruya yanıt verecek kayıt bulamadım."

    results = build_results(items_sorted)
    evidence = format_evidence(items_sorted, limit=5)

    llm = get_llm()
    prompt = build_prompt_rag(question, results, evidence)
    out = llm(prompt, max_tokens=300, temperature=0, top_p=1.0, stop=["<|im_end|>"])
    return out["choices"][0]["text"].strip()


def main():
    q = input("Soru: ").strip()
    if not q:
        print("EMPTY_QUESTION")
        return

    if is_report_question(q) and P_MONTHLY_TOTAL.exists():
        ans = answer_from_reports(q)
    else:
        ans = answer_from_rag(q)

    print("\n" + ans + "\n")


if __name__ == "__main__":
    main()
