"""
Subscription Tracker - Abonelik ve tekrarlayan ödeme takibi
"""
import sqlite3
from pathlib import Path
from typing import List, Dict
from collections import defaultdict
from datetime import datetime, timedelta

class SubscriptionTracker:
    """Tekrarlayan ödemeleri otomatik tespit eder"""
    
    def __init__(self, db_path: str = "data/spendrag.sqlite"):
        self.db_path = Path(db_path)
        self.tolerance = 0.05  # %5 tutar toleransı
    
    def detect_subscriptions(self, min_occurrences: int = 3) -> List[Dict]:
        """Tekrarlayan ödemeleri tespit et"""
        conn = sqlite3.connect(str(self.db_path))
        
        # Merchant bazlı harcamaları grupla
        rows = conn.execute("""
            SELECT r.merchant, i.name_norm, i.amount, r.receipt_date
            FROM items i
            JOIN receipts r ON i.receipt_id = r.id
            WHERE r.merchant IS NOT NULL
            AND i.amount > 0
            ORDER BY r.merchant, r.receipt_date
        """).fetchall()
        
        # Merchant ve ürün bazında grupla
        merchant_items = defaultdict(list)
        for merchant, name, amount, date in rows:
            key = f"{merchant}|{name}"
            merchant_items[key].append({"amount": amount, "date": date})
        
        subscriptions = []
        
        for key, transactions in merchant_items.items():
            if len(transactions) < min_occurrences:
                continue
            
            merchant, name = key.split("|", 1)
            
            # Tutarların benzer olup olmadığını kontrol et
            amounts = [t["amount"] for t in transactions]
            avg_amount = sum(amounts) / len(amounts)
            
            # Tüm tutarlar ortalamaya yakın mı?
            is_similar = all(
                abs(amt - avg_amount) / avg_amount <= self.tolerance
                for amt in amounts
            )
            
            if not is_similar:
                continue
            
            # Tarih aralıklarını hesapla
            dates = sorted([datetime.fromisoformat(t["date"]) for t in transactions])
            intervals = [(dates[i+1] - dates[i]).days for i in range(len(dates)-1)]
            
            if not intervals:
                continue
            
            avg_interval = sum(intervals) / len(intervals)
            
            # Düzenli mi? (ortalama ±7 gün tolerans)
            is_regular = all(abs(interval - avg_interval) <= 7 for interval in intervals)
            
            if is_regular:
                # Periyodu belirle
                if 25 <= avg_interval <= 35:
                    period = "monthly"
                    period_tr = "Aylık"
                elif 6 <= avg_interval <= 8:
                    period = "weekly"
                    period_tr = "Haftalık"
                else:
                    period = "custom"
                    period_tr = f"{int(avg_interval)} günde bir"
                
                # Sonraki ödeme tahmini
                last_date = dates[-1]
                next_payment = last_date + timedelta(days=int(avg_interval))
                days_until = (next_payment - datetime.now()).days
                
                subscriptions.append({
                    "merchant": merchant,
                    "name": name,
                    "amount": round(avg_amount, 2),
                    "period": period,
                    "period_tr": period_tr,
                    "frequency_months": len(transactions),
                    "last_payment": last_date.date().isoformat(),
                    "next_payment": next_payment.date().isoformat(),
                    "days_until_next": days_until,
                    "total_spent": round(sum(amounts), 2),
                    "annual_cost": round(avg_amount * (365 / avg_interval), 2)
                })
        
        conn.close()
        
        # Tutara göre sırala
        return sorted(subscriptions, key=lambda x: x["amount"], reverse=True)
    
    def get_upcoming_payments(self, days: int = 7) -> List[Dict]:
        """Yaklaşan ödemeleri getir"""
        subscriptions = self.detect_subscriptions()
        upcoming = [
            sub for sub in subscriptions
            if 0 <= sub["days_until_next"] <= days
        ]
        return sorted(upcoming, key=lambda x: x["days_until_next"])

# Global instance
_subscription_tracker = None

def get_subscription_tracker() -> SubscriptionTracker:
    """Singleton subscription tracker"""
    global _subscription_tracker
    if _subscription_tracker is None:
        _subscription_tracker = SubscriptionTracker()
    return _subscription_tracker
