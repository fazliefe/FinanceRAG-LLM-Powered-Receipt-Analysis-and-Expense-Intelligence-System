"""
Anomaly Detection - Anormal harcama tespiti
"""
import sqlite3
from pathlib import Path
from typing import List, Dict
import statistics

class AnomalyDetector:
    """İstatistiksel anormallik tespiti"""
    
    def __init__(self, db_path: str = "data/spendrag.sqlite"):
        self.db_path = Path(db_path)
        self.z_score_threshold = 2.5  # 2.5 standart sapma
    
    def detect_anomalies(self, days: int = 30) -> List[Dict]:
        """Son N gündeki anormal harcamaları tespit et"""
        conn = sqlite3.connect(str(self.db_path))
        
        # Kategori bazlı istatistikler
        anomalies = []
        
        # Her kategori için ayrı analiz
        categories = self._get_categories(conn)
        
        for category in categories:
            category_anomalies = self._detect_category_anomalies(conn, category, days)
            anomalies.extend(category_anomalies)
        
        conn.close()
        return anomalies
    
    def _get_categories(self, conn: sqlite3.Connection) -> List[str]:
        """Tüm kategorileri getir"""
        rows = conn.execute("SELECT DISTINCT category FROM items WHERE category IS NOT NULL").fetchall()
        return [row[0] for row in rows]
    
    def _detect_category_anomalies(self, conn: sqlite3.Connection, category: str, days: int) -> List[Dict]:
        """Belirli kategoride anormallikleri tespit et"""
        # Geçmiş harcamaları getir
        rows = conn.execute("""
            SELECT i.id, i.name_norm, i.amount, r.receipt_date, r.merchant
            FROM items i
            JOIN receipts r ON i.receipt_id = r.id
            WHERE i.category = ?
            AND r.receipt_date >= date('now', '-' || ? || ' days')
            AND i.amount > 0
            ORDER BY r.receipt_date DESC
        """, (category, days)).fetchall()
        
        if len(rows) < 5:  # Yeterli veri yok
            return []
        
        amounts = [row[2] for row in rows]
        mean = statistics.mean(amounts)
        
        try:
            stdev = statistics.stdev(amounts)
        except:
            return []  # Standart sapma hesaplanamadı
        
        if stdev == 0:
            return []
        
        anomalies = []
        for row in rows:
            item_id, name, amount, date, merchant = row
            z_score = (amount - mean) / stdev
            
            if abs(z_score) > self.z_score_threshold:
                anomalies.append({
                    "item_id": item_id,
                    "name": name,
                    "amount": amount,
                    "date": date,
                    "merchant": merchant,
                    "category": category,
                    "z_score": z_score,
                    "mean": mean,
                    "stdev": stdev,
                    "severity": "high" if abs(z_score) > 3 else "medium",
                    "message": self._format_anomaly_message(name, amount, mean, z_score, category)
                })
        
        return anomalies
    
    def _format_anomaly_message(self, name: str, amount: float, mean: float, z_score: float, category: str) -> str:
        """Anormallik mesajı oluştur"""
        if z_score > 0:
            return f"🔴 '{name}' için olağandışı yüksek harcama: {amount:.2f} TL (ortalama: {mean:.2f} TL, {category})"
        else:
            return f"🟢 '{name}' için olağandışı düşük harcama: {amount:.2f} TL (ortalama: {mean:.2f} TL, {category})"

# Global instance
_anomaly_detector = None

def get_anomaly_detector() -> AnomalyDetector:
    """Singleton anomaly detector"""
    global _anomaly_detector
    if _anomaly_detector is None:
        _anomaly_detector = AnomalyDetector()
    return _anomaly_detector
