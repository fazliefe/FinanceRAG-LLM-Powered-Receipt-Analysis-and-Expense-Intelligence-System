from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

OUT = Path("data/inbox/ornek_fis_migros.pdf")

TEXT = [
"MIGROS TICARET A.S.",
"Magaza: Migros MMM Istanbul Kadikoy",
"Adres : Rasimpasa Mah. Ornek Sok. No:12",
"Vergi No: 1234567890",
"",
"Tarih: 2025-12-20   Saat: 18:42",
"Fis No: 004218    Kasa: 03",
"",
"URUN                         ADET   TUTAR (TRY)",
"--------------------------------------------------------------",
"01 SUT 1 LT                    1        49,90",
"02 YOGURT 750G                 1        64,50",
"03 EKMEK TAM BUGDAY            1        19,90",
"04 YUMURTA 10LU                1        79,95",
"05 DOMATES 1.25 KG           1,25       62,38",
"06 MAKARNA 500G                2        39,80",
"07 BULASIK DETERJANI 750ML     1        89,90",
"08 SU 1.5LT                    6        59,40",
"--------------------------------------------------------------",
"Ara Toplam: 419,16 TRY",
"KDV (10%):   46,57 TRY",
"TOPLAM:     465,73 TRY",
"",
"Odeme: Kredi Karti",
"Tesekkur ederiz. Iade ve degisim icin fis ibraz ediniz.",
]

def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(OUT), pagesize=A4)
    width, height = A4

    y = height - 50
    for line in TEXT:
        c.drawString(50, y, line)
        y -= 14
        if y < 50:
            c.showPage()
            y = height - 50

    c.save()
    print(f"SAMPLE_PDF_OK: {OUT}")

if __name__ == "__main__":
    main()
