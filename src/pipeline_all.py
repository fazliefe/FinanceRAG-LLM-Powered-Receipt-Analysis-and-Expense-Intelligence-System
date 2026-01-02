from __future__ import annotations

from .ingest_pdf import main as ingest_main
from .extract_llm import main as extract_all_main
from .enrich_items import main as enrich_main
from .index_faiss import main as index_main
from .report_monthly import main as report_main


def main():
    # 1) Ingest PDFs -> receipts.raw_text
    ingest_main()

    # 2) Extract ALL receipts -> items
    extract_all_main()

    # 3) Enrich items (normalize + category)
    enrich_main()

    # 4) Rebuild FAISS index
    index_main()

    # 5) Rebuild reports
    report_main()

    print("PIPELINE_ALL_OK")


if __name__ == "__main__":
    main()
