from __future__ import annotations

from pathlib import Path
import sqlite3

import pandas as pd

DB_PATH = Path("data/spendrag.sqlite")
OUT_DIR = Path("data/reports")

def main():
    if not DB_PATH.exists():
        print("DB_MISSING")
        return

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    con = sqlite3.connect(str(DB_PATH))

    df = pd.read_sql_query(
        """
        SELECT
          r.receipt_date,
          r.merchant,
          r.source_path,
          i.name_raw,
          i.name_norm,
          i.category,
          i.qty,
          i.unit,
          i.amount
        FROM items i
        JOIN receipts r ON r.id = i.receipt_id
        WHERE r.receipt_date IS NOT NULL
        """,
        con,
    )
    con.close()

    if df.empty:
        print("NO_DATA")
        return

    # Ay kolonunu üret (YYYY-MM)
    df["month"] = df["receipt_date"].astype(str).str.slice(0, 7)

    # 1) Aylık toplam harcama (TRY)
    monthly_total = (
        df.groupby("month", as_index=False)["amount"]
        .sum()
        .rename(columns={"amount": "total_try"})
        .sort_values("month")
    )

    # 2) Aylık kategori kırılımı
    monthly_by_category = (
        df.groupby(["month", "category"], as_index=False)["amount"]
        .sum()
        .rename(columns={"amount": "total_try"})
        .sort_values(["month", "total_try"], ascending=[True, False])
    )

    # 3) Aylık en çok harcanan ürünler (top 20)
    top_items = (
        df.groupby(["month", "name_norm"], as_index=False)["amount"]
        .sum()
        .rename(columns={"amount": "total_try"})
        .sort_values(["month", "total_try"], ascending=[True, False])
    )
    top_items_20 = top_items.groupby("month").head(20).reset_index(drop=True)

    # CSV export
    p1 = OUT_DIR / "monthly_total.csv"
    p2 = OUT_DIR / "monthly_by_category.csv"
    p3 = OUT_DIR / "top_items_by_month_top20.csv"

    monthly_total.to_csv(p1, index=False, encoding="utf-8")
    monthly_by_category.to_csv(p2, index=False, encoding="utf-8")
    top_items_20.to_csv(p3, index=False, encoding="utf-8")

    print("REPORT_OK")
    print(f"- {p1}")
    print(f"- {p2}")
    print(f"- {p3}")

    # Konsolda da kısa özet göster
    print("\nMONTHLY_TOTAL (preview):")
    print(monthly_total.tail(12).to_string(index=False))

if __name__ == "__main__":
    main()
