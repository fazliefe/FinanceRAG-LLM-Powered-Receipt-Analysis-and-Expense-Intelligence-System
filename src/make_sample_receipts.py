from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

INBOX_DIR = Path("data/inbox")

def fmt_tr(x: float) -> str:
    # 1234.56 -> "1234,56"
    return f"{x:.2f}".replace(".", ",")

def make_pdf(path: Path, lines: list[str]) -> None:
    c = canvas.Canvas(str(path), pagesize=A4)
    width, height = A4
    y = height - 50
    for line in lines:
        c.drawString(50, y, line)
        y -= 14
        if y < 50:
            c.showPage()
            y = height - 50
    c.save()

def build_receipt(merchant, store, date_str, time_str, receipt_no, kasa, items):
    # items: list of (name, qty, amount)
    subtotal = sum(a for _, _, a in items)
    kdv = round(subtotal * 0.10, 2)
    total = round(subtotal + kdv, 2)

    lines = [
        f"{merchant}",
        f"Magaza: {store}",
        "Adres : Ornek Mah. Ornek Sok. No:12",
        "Vergi No: 1234567890",
        "",
        f"Tarih: {date_str}   Saat: {time_str}",
        f"Fis No: {receipt_no}    Kasa: {kasa}",
        "",
        "URUN                         ADET   TUTAR (TRY)",
        "--------------------------------------------------------------",
    ]

    for i, (name, qty, amt) in enumerate(items, start=1):
        # qty format: 1,25 gibi
        if isinstance(qty, float) and not qty.is_integer():
            qty_str = str(qty).replace(".", ",")
        elif isinstance(qty, (int, float)):
            qty_str = str(int(qty))
        else:
            qty_str = str(qty)

        lines.append(f"{i:02d} {name:<26} {qty_str:>5}   {fmt_tr(amt):>10}")

    lines += [
        "--------------------------------------------------------------",
        f"Ara Toplam: {fmt_tr(subtotal)} TRY",
        f"KDV (10%):   {fmt_tr(kdv)} TRY",
        f"TOPLAM:     {fmt_tr(total)} TRY",
        "",
        "Odeme: Kredi Karti",
        "Tesekkur ederiz. Iade ve degisim icin fis ibraz ediniz.",
    ]
    return lines

def main():
    INBOX_DIR.mkdir(parents=True, exist_ok=True)

    receipts_specs = [
        ("A101", "A101 Istanbul Kadikoy", "2025-11-25", "19:05", "001102", "02",
         [("SUT 1 LT",1,42.50),("YOGURT 1KG",1,78.90),("EKMEK",2,16.00),("BULASIK SINGERI",1,29.90),("SU 1.5LT",6,54.00)]),

        ("BIM", "BIM Istanbul Uskudar", "2025-12-02", "18:12", "008771", "01",
         [("MAKARNA 500G",3,54.00),("DOMATES 1.00 KG",1.0,38.75),("YUMURTA 10LU",1,74.95),("YOGURT 750G",1,62.50),("DETERJAN 1.5L",1,119.90)]),

        ("SOK", "SOK Market Istanbul Maltepe", "2025-12-10", "20:41", "004905", "03",
         [("SUT 1 LT",2,86.00),("PEYNIR 500G",1,129.90),("SU 0.5LT",12,78.00),("SAMPUAN 400ML",1,99.90)]),

        ("CARREFOURSA", "CarrefourSA Istanbul Atasehir", "2025-12-15", "17:33", "006214", "04",
         [("YOGURT 2KG",1,159.90),("TAVUK 1.20 KG",1.2,154.80),("BULASIK DETERJANI 750ML",1,94.90),("KAGIT HAVLU",1,89.90)]),

        ("MIGROS TICARET A.S.", "Migros MMM Istanbul Kadikoy", "2025-12-18", "12:08", "004877", "05",
         [("MEYVE SUYU 1L",2,74.00),("YOGURT 750G",1,66.90),("DOMATES 1.50 KG",1.5,79.50),("DIS MACUNU",1,69.90)]),

        ("ONLINE MARKET", "Online Siparis", "2025-12-21", "10:22", "009991", "WEB",
         [("SU 19L DAMACANA",1,89.00),("KAHVE 250G",1,139.90),("MAKARNA 500G",4,72.00),("YOGURT 1KG",1,82.50)]),
    ]

    made = 0
    for merchant, store, d, t, no, kasa, items in receipts_specs:
        short = merchant.split()[0].lower()
        out = INBOX_DIR / f"ornek_fis_{short}_{d}.pdf"
        lines = build_receipt(merchant, store, d, t, no, kasa, items)
        make_pdf(out, lines)
        made += 1

    print(f"SAMPLE_RECEIPTS_OK: created={made} folder={INBOX_DIR}")

if __name__ == "__main__":
    main()
