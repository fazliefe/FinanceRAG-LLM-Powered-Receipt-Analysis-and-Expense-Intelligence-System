"""
PDF Report Generator - Detaylı PDF raporları oluşturur
"""
from pathlib import Path
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
import sqlite3

class PDFReportGenerator:
    """PDF rapor oluşturucu"""
    
    def __init__(self, db_path: str = "data/spendrag.sqlite"):
        self.db_path = Path(db_path)
        self.styles = getSampleStyleSheet()
        self._setup_styles()
    
    def _setup_styles(self):
        """Özel stiller ekle"""
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#4338ca'),
            spaceAfter=30,
            alignment=TA_CENTER
        ))
        
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#1e293b'),
            spaceBefore=20,
            spaceAfter=10
        ))
    
    def generate_monthly_report(self, year: int, month: int, output_path: str = None) -> str:
        """Aylık rapor oluştur"""
        if output_path is None:
            output_path = f"data/reports/monthly_report_{year}_{month:02d}.pdf"
        
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        doc = SimpleDocTemplate(output_path, pagesize=A4)
        story = []
        
        # Başlık
        title = Paragraph(f"Harcama Raporu - {month:02d}/{year}", self.styles['CustomTitle'])
        story.append(title)
        story.append(Spacer(1, 0.5*cm))
        
        # Özet İstatistikler
        stats = self._get_monthly_stats(year, month)
        story.append(Paragraph("📊 Özet İstatistikler", self.styles['SectionHeader']))
        story.append(self._create_stats_table(stats))
        story.append(Spacer(1, 0.5*cm))
        
        # Kategori Bazlı Harcamalar
        story.append(Paragraph("🛍️ Kategori Bazlı Harcamalar", self.styles['SectionHeader']))
        category_data = self._get_category_breakdown(year, month)
        story.append(self._create_category_table(category_data))
        story.append(Spacer(1, 0.5*cm))
        
        # En Çok Harcama Yapılan Yerler
        story.append(Paragraph("🏪 En Çok Harcama Yapılan Yerler", self.styles['SectionHeader']))
        merchant_data = self._get_top_merchants(year, month, limit=10)
        story.append(self._create_merchant_table(merchant_data))
        
        # PDF oluştur
        doc.build(story)
        return output_path
    
    def _get_monthly_stats(self, year: int, month: int) -> dict:
        """Aylık istatistikleri getir"""
        conn = sqlite3.connect(str(self.db_path))
        
        start_date = f"{year}-{month:02d}-01"
        end_date = f"{year}-{month:02d}-31"
        
        total = conn.execute("""
            SELECT SUM(i.amount)
            FROM items i
            JOIN receipts r ON i.receipt_id = r.id
            WHERE r.receipt_date BETWEEN ? AND ?
        """, (start_date, end_date)).fetchone()[0] or 0
        
        receipt_count = conn.execute("""
            SELECT COUNT(DISTINCT r.id)
            FROM receipts r
            WHERE r.receipt_date BETWEEN ? AND ?
        """, (start_date, end_date)).fetchone()[0] or 0
        
        item_count = conn.execute("""
            SELECT COUNT(i.id)
            FROM items i
            JOIN receipts r ON i.receipt_id = r.id
            WHERE r.receipt_date BETWEEN ? AND ?
        """, (start_date, end_date)).fetchone()[0] or 0
        
        conn.close()
        
        return {
            "total_spent": total,
            "receipt_count": receipt_count,
            "item_count": item_count,
            "avg_per_receipt": total / receipt_count if receipt_count > 0 else 0
        }
    
    def _get_category_breakdown(self, year: int, month: int) -> list:
        """Kategori bazlı harcamaları getir"""
        conn = sqlite3.connect(str(self.db_path))
        
        start_date = f"{year}-{month:02d}-01"
        end_date = f"{year}-{month:02d}-31"
        
        rows = conn.execute("""
            SELECT i.category, SUM(i.amount) as total, COUNT(i.id) as count
            FROM items i
            JOIN receipts r ON i.receipt_id = r.id
            WHERE r.receipt_date BETWEEN ? AND ?
            GROUP BY i.category
            ORDER BY total DESC
        """, (start_date, end_date)).fetchall()
        
        conn.close()
        return rows
    
    def _get_top_merchants(self, year: int, month: int, limit: int = 10) -> list:
        """En çok harcama yapılan yerleri getir"""
        conn = sqlite3.connect(str(self.db_path))
        
        start_date = f"{year}-{month:02d}-01"
        end_date = f"{year}-{month:02d}-31"
        
        rows = conn.execute("""
            SELECT r.merchant, SUM(i.amount) as total, COUNT(DISTINCT r.id) as visits
            FROM items i
            JOIN receipts r ON i.receipt_id = r.id
            WHERE r.receipt_date BETWEEN ? AND ?
            GROUP BY r.merchant
            ORDER BY total DESC
            LIMIT ?
        """, (start_date, end_date, limit)).fetchall()
        
        conn.close()
        return rows
    
    def _create_stats_table(self, stats: dict) -> Table:
        """İstatistik tablosu oluştur"""
        data = [
            ['Toplam Harcama', f"{stats['total_spent']:.2f} TL"],
            ['Fiş Sayısı', str(stats['receipt_count'])],
            ['Ürün Sayısı', str(stats['item_count'])],
            ['Fiş Başına Ortalama', f"{stats['avg_per_receipt']:.2f} TL"]
        ]
        
        table = Table(data, colWidths=[10*cm, 5*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8f9fa')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey)
        ]))
        
        return table
    
    def _create_category_table(self, data: list) -> Table:
        """Kategori tablosu oluştur"""
        table_data = [['Kategori', 'Toplam', 'Adet']]
        for row in data:
            table_data.append([row[0], f"{row[1]:.2f} TL", str(row[2])])
        
        table = Table(table_data, colWidths=[8*cm, 4*cm, 3*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4338ca')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        return table
    
    def _create_merchant_table(self, data: list) -> Table:
        """Market tablosu oluştur"""
        table_data = [['Market', 'Toplam', 'Ziyaret']]
        for row in data:
            table_data.append([row[0] or 'Bilinmeyen', f"{row[1]:.2f} TL", str(row[2])])
        
        table = Table(table_data, colWidths=[8*cm, 4*cm, 3*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4338ca')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        return table

# Global instance
_pdf_generator = None

def get_pdf_generator() -> PDFReportGenerator:
    """Singleton PDF generator"""
    global _pdf_generator
    if _pdf_generator is None:
        _pdf_generator = PDFReportGenerator()
    return _pdf_generator
