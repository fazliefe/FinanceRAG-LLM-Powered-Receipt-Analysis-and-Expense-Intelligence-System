from __future__ import annotations

import csv
from pathlib import Path

from llama_cpp import Llama

LLM_MODEL_PATH = r"models\qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf"

REPORT_DIR = Path("data/reports")
P_MONTHLY_TOTAL = REPORT_DIR / "monthly_total.csv"
P_MONTHLY_CAT = REPORT_DIR / "monthly_by_category.csv"
P_TOP_ITEMS = REPORT_DIR / "top_items_by_month_top20.csv"

PROMPT = """<|im_start|>system
Sen, kişisel harcama raporlarını açıklayan bir asistansın.
Sana "RAPOR_VERISI" verilecek.

Kurallar:
- Sadece RAPOR_VERISI'ne dayan.
- Hesap yapma; sayılar zaten rapordan geliyor.
- Cevap kısa ve net olsun.
- Eğer kullanıcı bir ay belirtmişse, o aya odaklan.
- Eğer ay belirtilmemişse mevcut ayları listele ve soru sor (tek cümleyle).

<|im_end|>
<|im_start|>user
SORU:
{question}

RAPOR_VERISI:
{report_data}
<|im_end|>
<|im_start|>assistant
"""

def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def pick_month(question: str, months: list[str]) -> str | None:
    q = question.strip()
    # 2025-12 gibi
    import re
    m = re.search(r"(20\d{2})[-/](\d{1,2})", q)
    if m:
        y = m.group(1)
        mo = int(m.group(2))
        return f"{y}-{mo:02d}"
    # "bu ay" yok; MVP: sadece explicit
    return None

def main():
    question = input("Rapor sorusu: ").strip()
    if not question:
        print("EMPTY_QUESTION")
        return

    monthly_total = read_csv(P_MONTHLY_TOTAL)
    monthly_cat = read_csv(P_MONTHLY_CAT)
    top_items = read_csv(P_TOP_ITEMS)

    months = sorted({r["month"] for r in monthly_total if r.get("month")})

    target_month = pick_month(question, months)

    # Rapordan seçili ay verisini derle
    report = {"available_months": months}

    if target_month:
        report["target_month"] = target_month
        report["monthly_total"] = [r for r in monthly_total if r.get("month") == target_month]
        report["monthly_by_category"] = [r for r in monthly_cat if r.get("month") == target_month]
        report["top_items_top10"] = [r for r in top_items if r.get("month") == target_month][:10]
    else:
        report["note"] = "Soru içinde ay (YYYY-MM) belirtilmedi."

    llm = Llama(
        model_path=LLM_MODEL_PATH,
        n_ctx=2048,
        n_threads=8,
        verbose=False,
    )

    prompt = PROMPT.format(question=question, report_data=report)
    out = llm(prompt, max_tokens=250, temperature=0, top_p=1.0, stop=["<|im_end|>"])
    print("\n" + out["choices"][0]["text"].strip() + "\n")

if __name__ == "__main__":
    main()
