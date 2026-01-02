from __future__ import annotations

import json
import re
import sqlite3
import uuid
from pathlib import Path

from llama_cpp import Llama

from .db import connect, init_schema

MODEL_PATH = r"models\qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf"
PROMPT_PATH = Path("prompts/extract_receipt_tr.txt")


def load_prompt(text: str) -> str:
    tpl = PROMPT_PATH.read_text(encoding="utf-8")
    return tpl.replace("{{TEXT}}", text)


def coerce_number(x):
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return float(x)
    s = str(x).strip()
    if not s:
        return None
    s = s.replace(" ", "")
    if re.search(r"\d+\.\d+,\d+", s):
        s = s.replace(".", "").replace(",", ".")
    else:
        s = s.replace(",", ".")
    try:
        return float(s)
    except:
        return None


def fix_decimal_commas_outside_strings(s: str) -> str:
    out = []
    in_str = False
    esc = False
    n = len(s)
    for i, ch in enumerate(s):
        if in_str:
            out.append(ch)
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
            out.append(ch)
            continue
        if ch == ",":
            prev = s[i - 1] if i > 0 else ""
            nxt = s[i + 1] if i + 1 < n else ""
            if prev.isdigit() and nxt.isdigit():
                out.append(".")
                continue
        out.append(ch)
    return "".join(out)


def repair_json_blob(blob: str) -> str:
    blob2 = fix_decimal_commas_outside_strings(blob)
    blob2 = re.sub(r",\s*([}\]])", r"\1", blob2)
    blob2 = re.sub(r"\bNone\b", "null", blob2)
    return blob2


def extract_first_json(s: str) -> dict:
    start = s.find("{")
    end = s.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in model output.")
    blob = s[start : end + 1]

    Path("data").mkdir(parents=True, exist_ok=True)
    Path("data/last_llm_output.txt").write_text(s, encoding="utf-8", errors="ignore")
    Path("data/last_json_blob.txt").write_text(blob, encoding="utf-8", errors="ignore")

    try:
        return json.loads(blob)
    except json.JSONDecodeError:
        fixed = repair_json_blob(blob)
        Path("data/last_json_blob_fixed.txt").write_text(fixed, encoding="utf-8", errors="ignore")
        return json.loads(fixed)


def upsert_receipt_fields(conn: sqlite3.Connection, rid: str, merchant: str, date: str, currency: str, total_amount):
    conn.execute(
        """
        UPDATE receipts
        SET merchant = ?, receipt_date = ?, currency = ?, total_amount = ?
        WHERE id = ?
        """,
        (merchant or None, date or None, currency or "TRY", coerce_number(total_amount), rid),
    )


def insert_items(conn: sqlite3.Connection, rid: str, items: list[dict]):
    conn.execute("DELETE FROM items WHERE receipt_id = ?", (rid,))
    for idx, it in enumerate(items, start=1):
        name = (it.get("name") or "").strip()
        if not name:
            continue
        item_id = str(uuid.uuid4())
        qty = coerce_number(it.get("qty"))
        unit = it.get("unit")
        unit = unit.strip() if isinstance(unit, str) and unit.strip() else None
        amount = coerce_number(it.get("amount"))
        evidence = name[:160]
        conn.execute(
            """
            INSERT INTO items (id, receipt_id, name_raw, qty, unit, amount, line_no, evidence_snippet)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (item_id, rid, name, qty, unit, amount, idx, evidence),
        )


def receipt_needs_extraction(row) -> bool:
    # merchant/date/total boşsa veya items yoksa tekrar çıkar
    rid = row[0]
    merchant = row[1]
    receipt_date = row[2]
    total_amount = row[3]
    item_count = row[4]
    if item_count == 0:
        return True
    if (merchant is None) or (receipt_date is None) or (total_amount is None):
        return True
    return False


def main():
    conn = connect()
    init_schema(conn)

    rows = conn.execute(
        """
        SELECT
          r.id,
          r.merchant,
          r.receipt_date,
          r.total_amount,
          (SELECT COUNT(*) FROM items i WHERE i.receipt_id = r.id) as item_count,
          r.raw_text
        FROM receipts r
        ORDER BY r.rowid
        """
    ).fetchall()

    if not rows:
        print("NO_RECEIPTS")
        return

    llm = Llama(model_path=MODEL_PATH, n_ctx=4096, n_threads=8, verbose=False)

    processed = 0
    skipped = 0

    for (rid, merchant, receipt_date, total_amount, item_count, raw_text) in rows:
        if not receipt_needs_extraction((rid, merchant, receipt_date, total_amount, item_count)):
            skipped += 1
            continue

        prompt = load_prompt(raw_text)
        out = llm(prompt, max_tokens=1024, temperature=0, top_p=1.0, stop=["<|im_end|>"])
        text = out["choices"][0]["text"]
        data = extract_first_json(text)

        m = (data.get("merchant") or "").strip()
        d = (data.get("date") or "").strip()
        cur = (data.get("currency") or "TRY").strip()
        tot = data.get("total_amount")
        items = data.get("items") or []

        upsert_receipt_fields(conn, rid, m, d, cur, tot)
        insert_items(conn, rid, items)
        conn.commit()

        processed += 1
        print(f"EXTRACT_ONE_OK: receipt_id={rid} items={(len(items))} merchant={m} date={d} total={coerce_number(tot)} {cur}")

    conn.close()
    print(f"EXTRACT_ALL_DONE: processed={processed} skipped={skipped} receipts_total={len(rows)}")


if __name__ == "__main__":
    main()
