from __future__ import annotations

import sqlite3
from pathlib import Path

import pdfplumber
from tqdm import tqdm

from .db import connect, init_schema

# OCR imports (optional)
try:
    from pdf2image import convert_from_path
    import pytesseract
except Exception:
    convert_from_path = None
    pytesseract = None

INBOX_DIR = Path("data/inbox")

# Eğer tesseract PATH'te değilse buraya yaz:
TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Eğer poppler PATH'te değilse buraya bin klasörünü yaz:
POPPLER_BIN = r"C:\poppler\Library\bin"

def extract_text_from_pdf(pdf_path: Path) -> str:
    # 1) Normal text extraction (pdfplumber)
    text_parts: list[str] = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            t = page.extract_text() or ""
            t = t.strip()
            text_parts.append(f"[PAGE {i}]\n{t}\n")
    raw = "\n".join(text_parts).strip()
    return raw

def ocr_pdf(pdf_path: Path) -> str:
    if convert_from_path is None or pytesseract is None:
        return ""

    # configure tesseract path
    try:
        pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
    except Exception:
        pass

    try:
        images = convert_from_path(str(pdf_path), dpi=250, poppler_path=POPPLER_BIN)
    except Exception:
        # poppler_path yanlışsa PATH'ten dene
        images = convert_from_path(str(pdf_path), dpi=250)

    out_parts: list[str] = []
    for i, img in enumerate(images, start=1):
        # Türkçe OCR için lang="tur" (tur traineddata yüklüyse)
        try:
            txt = pytesseract.image_to_string(img, lang="tur")
        except Exception:
            txt = pytesseract.image_to_string(img)
        txt = (txt or "").strip()
        out_parts.append(f"[PAGE {i} OCR]\n{txt}\n")

    return "\n".join(out_parts).strip()

def ingest_one(conn: sqlite3.Connection, pdf_path: Path) -> str | None:
    # zaten var mı?
    row = conn.execute("SELECT id FROM receipts WHERE source_path = ?", (str(pdf_path),)).fetchone()
    if row:
        return None

    # önce normal extraction
    raw_text = ""
    try:
        raw_text = extract_text_from_pdf(pdf_path)
    except Exception:
        raw_text = ""

    # boşsa veya çok kısa ise OCR/VLM dene
    if not raw_text or len(raw_text) < 30:
        ocr_text = ""
        vlm_text = ""
        
        # OCR denemesi (Poppler gerektirir)
        try:
            ocr_text = ocr_pdf(pdf_path)
        except Exception as e:
            print(f"⚠️  OCR skipped (Poppler not installed or error): {e}")
        
        # VLM Denemesi (Yeni Premium - Poppler + VLM model gerektirir)
        try:
            from .vlm import analyze_receipt_image
            # Geçici resim dosyası oluştur
            if convert_from_path:
                images = convert_from_path(str(pdf_path), first_page=1, last_page=1, dpi=200)
                if images:
                    tmp_img = pdf_path.with_suffix(".jpg")
                    images[0].save(tmp_img, "JPEG")
                    vlm_json = analyze_receipt_image(str(tmp_img))
                    if vlm_json and vlm_json.strip():
                        vlm_text = f"VLM_EXTRACTED_JSON:\n{vlm_json}"
                    # Temizlik
                    if tmp_img.exists():
                        tmp_img.unlink()
        except Exception as e:
            print(f"⚠️  VLM skipped (dependencies missing or error): {e}")

        # Hangisi daha iyiyse onu al (basit mantık: uzunluk)
        candidates = [t for t in [ocr_text, vlm_text] if t]
        if candidates:
            # En uzun metni seç (genelde daha fazla detay içerir)
            best_candidate = max(candidates, key=len)
            if len(best_candidate) > len(raw_text):
                raw_text = best_candidate

    if not raw_text:
        raw_text = ""

    # Calculate hash for deduplication
    import hashlib
    raw_text_hash = hashlib.sha256(raw_text.encode('utf-8')).hexdigest()

    rid = conn.execute(
        "INSERT INTO receipts (source_path, raw_text, raw_text_hash) VALUES (?, ?, ?) RETURNING id",
        (str(pdf_path), raw_text, raw_text_hash),
    ).fetchone()[0]

    return rid

def main():
    INBOX_DIR.mkdir(parents=True, exist_ok=True)

    conn = connect()
    init_schema(conn)

    pdfs = sorted(INBOX_DIR.glob("*.pdf"))
    ingested = 0
    skipped = 0
    empty = 0

    for p in tqdm(pdfs, desc="Ingesting PDFs"):
        rid = ingest_one(conn, p)
        if rid is None:
            skipped += 1
            continue
        ingested += 1

        ln = conn.execute("SELECT length(raw_text) FROM receipts WHERE id = ?", (rid,)).fetchone()[0] or 0
        if ln == 0:
            empty += 1

        conn.commit()

    total = conn.execute("SELECT count(*) FROM receipts").fetchone()[0]
    conn.close()

    print(f"INGEST_DONE: ingested={ingested} skipped={skipped} empty={empty} db_receipts_total={total}")

if __name__ == "__main__":
    main()
