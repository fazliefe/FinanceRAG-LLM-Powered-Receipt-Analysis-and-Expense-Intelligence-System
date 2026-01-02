from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from PIL import Image, ImageDraw, ImageFont
import io

INBOX_DIR = Path("data/inbox")

def create_receipt_image():
    """Create a realistic receipt image for VLM testing"""
    # Create image (thermal receipt size: 300px wide, variable height)
    width, height = 600, 1000
    img = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(img)
    
    # Try to use a monospace font, fallback to default
    try:
        font_large = ImageFont.truetype("consola.ttf", 28)
        font_medium = ImageFont.truetype("consola.ttf", 22)
        font_small = ImageFont.truetype("consola.ttf", 18)
    except:
        font_large = ImageFont.load_default()
        font_medium = ImageFont.load_default()
        font_small = ImageFont.load_default()
    
    y = 30
    
    # Header
    draw.text((width//2, y), "MİGROS", fill='black', font=font_large, anchor="mt")
    y += 40
    draw.text((width//2, y), "TICARET A.Ş.", fill='black', font=font_medium, anchor="mt")
    y += 35
    
    # Store info
    lines = [
        "Mağaza: Migros MMM Kadıköy",
        "Bağdat Cad. No:123",
        "Kadıköy/İSTANBUL",
        "Vergi No: 1234567890",
        "",
        "Tarih: 30.12.2024  Saat: 14:35",
        "Fiş No: 008842   Kasa: 03",
        "",
        "ÜRÜN                  ADET    TUTAR",
        "=" * 45,
    ]
    
    for line in lines:
        draw.text((30, y), line, fill='black', font=font_small)
        y += 25
    
    # Items
    items = [
        ("SÜT 1L", "2", "28,50", "57,00"),
        ("EKMEK", "3", "7,50", "22,50"),
        ("DOMATES 1KG", "1,5", "35,00", "52,50"),
        ("PEYNİR BEYAZ 500G", "1", "89,90", "89,90"),
        ("DETERJAN 3KG", "1", "145,00", "145,00"),
    ]
    
    for idx, (name, qty, price, total) in enumerate(items, 1):
        line = f"{idx:02d} {name:<20} {qty:>4}  {total:>7}"
        draw.text((30, y), line, fill='black', font=font_small)
        y += 25
    
    # Separator
    draw.text((30, y), "=" * 45, fill='black', font=font_small)
    y += 30
    
    # Totals
    totals = [
        "ARA TOPLAM:              366,90 TL",
        "KDV %20:                  61,15 TL",
        "",
    ]
    
    for line in totals:
        draw.text((30, y), line, fill='black', font=font_small)
        y += 25
    
    # Grand total (bold effect with multiple draws)
    total_text = "TOPLAM:                  428,05 TL"
    for offset in [(0,0), (1,0), (0,1), (1,1)]:
        draw.text((30 + offset[0], y + offset[1]), total_text, fill='black', font=font_medium)
    y += 40
    
    # Payment
    payment_lines = [
        "",
        "NAKİT:                   500,00 TL",
        "PARA ÜSTÜ:                71,95 TL",
        "",
        "",
        "TEŞEKKÜR EDERİZ",
        "İade için fiş saklayınız",
    ]
    
    for line in payment_lines:
        draw.text((width//2, y), line, fill='black', font=font_small, anchor="mt")
        y += 25
    
    # Add some noise for realism
    return img

def create_image_receipt_pdf():
    """Create a PDF with the receipt image embedded"""
    img = create_receipt_image()
    
    # Save as temporary image
    img_path = INBOX_DIR / "temp_receipt.png"
    img.save(img_path, "PNG")
    
    # Create PDF with image
    pdf_path = INBOX_DIR / "test_receipt_visual.pdf"
    c = canvas.Canvas(str(pdf_path), pagesize=A4)
    width, height = A4
    
    # Center the receipt image on the page
    img_width = 300
    img_height = 500
    x = (width - img_width) / 2
    y = (height - img_height) / 2
    
    c.drawImage(str(img_path), x, y, width=img_width, height=img_height)
    c.save()
    
    # Clean up temp image
    img_path.unlink()
    
    print(f"✅ Visual receipt created: {pdf_path}")
    return pdf_path

def main():
    INBOX_DIR.mkdir(parents=True, exist_ok=True)
    
    # Create visual receipt
    visual_pdf = create_image_receipt_pdf()
    
    print(f"\n🎯 Test Receipt Created!")
    print(f"   Location: {visual_pdf}")
    print(f"   This receipt contains an IMAGE (not text) to test VLM capabilities.")

if __name__ == "__main__":
    main()
