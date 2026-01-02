"""
Budget Management - Bütçe yönetimi ve uyarı sistemi
"""
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import uuid

class BudgetManager:
    """Bütçe yönetimi sistemi"""
    
    def __init__(self, db_path: str = "data/spendrag.sqlite"):
        self.db_path = Path(db_path)
        self._init_schema()
    
    def _init_schema(self):
        """Bütçe tablolarını oluştur"""
        conn = sqlite3.connect(str(self.db_path))
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS budgets (
                id TEXT PRIMARY KEY,
                category TEXT,
                period TEXT,
                limit_amount REAL,
                start_date TEXT,
                end_date TEXT,
                alert_threshold REAL DEFAULT 0.8,
                created_at TEXT
            );
            
            CREATE TABLE IF NOT EXISTS budget_alerts (
                id TEXT PRIMARY KEY,
                budget_id TEXT,
                alert_date TEXT,
                spent_amount REAL,
                limit_amount REAL,
                alert_type TEXT,
                acknowledged BOOLEAN DEFAULT 0,
                FOREIGN KEY(budget_id) REFERENCES budgets(id)
            );
        """)
        conn.commit()
        conn.close()
    
    def create_budget(
        self,
        category: str,
        limit_amount: float,
        period: str = "monthly",
        alert_threshold: float = 0.8
    ) -> str:
        """Yeni bütçe oluştur"""
        budget_id = str(uuid.uuid4())
        
        # Dönem başlangıç ve bitiş tarihlerini hesapla
        now = datetime.now()
        if period == "monthly":
            start_date = now.replace(day=1).date().isoformat()
            # Sonraki ayın ilk günü - 1 gün
            next_month = now.replace(day=28) + timedelta(days=4)
            end_date = (next_month.replace(day=1) - timedelta(days=1)).date().isoformat()
        elif period == "weekly":
            start_date = (now - timedelta(days=now.weekday())).date().isoformat()
            end_date = (now + timedelta(days=6 - now.weekday())).date().isoformat()
        else:
            start_date = now.date().isoformat()
            end_date = (now + timedelta(days=30)).date().isoformat()
        
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("""
            INSERT INTO budgets (id, category, period, limit_amount, start_date, end_date, alert_threshold, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (budget_id, category, period, limit_amount, start_date, end_date, alert_threshold, datetime.now().isoformat()))
        conn.commit()
        conn.close()
        
        return budget_id
    
    def get_active_budgets(self) -> List[Dict]:
        """Aktif bütçeleri getir"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        rows = cursor.execute("""
            SELECT id, category, period, limit_amount, start_date, end_date, alert_threshold
            FROM budgets
            WHERE end_date >= date('now')
            ORDER BY category
        """).fetchall()
        
        budgets = []
        for row in rows:
            budget = {
                "id": row[0],
                "category": row[1],
                "period": row[2],
                "limit_amount": row[3],
                "start_date": row[4],
                "end_date": row[5],
                "alert_threshold": row[6]
            }
            
            # Harcama miktarını hesapla
            spent = self._get_spent_amount(conn, budget["category"], budget["start_date"], budget["end_date"])
            budget["spent_amount"] = spent
            budget["remaining"] = budget["limit_amount"] - spent
            budget["usage_percent"] = (spent / budget["limit_amount"]) * 100 if budget["limit_amount"] > 0 else 0
            
            budgets.append(budget)
        
        conn.close()
        return budgets
    
    def _get_spent_amount(self, conn: sqlite3.Connection, category: str, start_date: str, end_date: str) -> float:
        """Belirli kategoride harcanan miktarı hesapla"""
        row = conn.execute("""
            SELECT SUM(i.amount)
            FROM items i
            JOIN receipts r ON i.receipt_id = r.id
            WHERE i.category = ?
            AND r.receipt_date BETWEEN ? AND ?
        """, (category, start_date, end_date)).fetchone()
        
        return row[0] if row[0] else 0.0
    
    def check_alerts(self) -> List[Dict]:
        """Bütçe uyarılarını kontrol et"""
        budgets = self.get_active_budgets()
        alerts = []
        
        conn = sqlite3.connect(str(self.db_path))
        
        for budget in budgets:
            usage_percent = budget["usage_percent"] / 100
            threshold = budget["alert_threshold"]
            
            alert_type = None
            if usage_percent >= 1.2:
                alert_type = "critical"
            elif usage_percent >= 1.0:
                alert_type = "exceeded"
            elif usage_percent >= threshold:
                alert_type = "warning"
            
            if alert_type:
                # Uyarı kaydet
                alert_id = str(uuid.uuid4())
                conn.execute("""
                    INSERT INTO budget_alerts (id, budget_id, alert_date, spent_amount, limit_amount, alert_type)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    alert_id,
                    budget["id"],
                    datetime.now().isoformat(),
                    budget["spent_amount"],
                    budget["limit_amount"],
                    alert_type
                ))
                
                alerts.append({
                    "id": alert_id,
                    "category": budget["category"],
                    "spent": budget["spent_amount"],
                    "limit": budget["limit_amount"],
                    "usage_percent": budget["usage_percent"],
                    "type": alert_type,
                    "message": self._format_alert_message(budget, alert_type)
                })
        
        conn.commit()
        conn.close()
        
        return alerts
    
    def _format_alert_message(self, budget: Dict, alert_type: str) -> str:
        """Uyarı mesajı oluştur"""
        category = budget["category"]
        spent = budget["spent_amount"]
        limit = budget["limit_amount"]
        percent = budget["usage_percent"]
        
        if alert_type == "critical":
            return f"🚨 {category} bütçeniz %{percent:.0f} aşıldı! ({spent:.2f} TL / {limit:.2f} TL)"
        elif alert_type == "exceeded":
            return f"⚠️ {category} bütçeniz aşıldı! ({spent:.2f} TL / {limit:.2f} TL)"
        else:
            return f"⚡ {category} bütçenizin %{percent:.0f}'i kullanıldı ({spent:.2f} TL / {limit:.2f} TL)"
    
    def delete_budget(self, budget_id: str):
        """Bütçeyi sil"""
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("DELETE FROM budgets WHERE id = ?", (budget_id,))
        conn.execute("DELETE FROM budget_alerts WHERE budget_id = ?", (budget_id,))
        conn.commit()
        conn.close()

# Global instance
_budget_manager = None

def get_budget_manager() -> BudgetManager:
    """Singleton budget manager"""
    global _budget_manager
    if _budget_manager is None:
        _budget_manager = BudgetManager()
    return _budget_manager
