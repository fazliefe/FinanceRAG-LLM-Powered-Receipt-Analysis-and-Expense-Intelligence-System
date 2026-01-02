"""
Cache System - Soru-cevap cache'leme
"""
import sqlite3
import hashlib
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

class QueryCache:
    """Soru-cevap cache sistemi"""
    
    def __init__(self, db_path: str = "data/cache.sqlite"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Cache veritabanını oluştur"""
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS query_cache (
                query_hash TEXT PRIMARY KEY,
                query_text TEXT NOT NULL,
                response TEXT NOT NULL,
                model_type TEXT,
                created_at TEXT NOT NULL,
                hit_count INTEGER DEFAULT 1,
                last_hit_at TEXT
            )
        """)
        conn.commit()
        conn.close()
    
    def _hash_query(self, query: str) -> str:
        """Sorguyu hash'le"""
        normalized = query.lower().strip()
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def get(self, query: str, max_age_hours: int = 24) -> Optional[str]:
        """Cache'den yanıt getir"""
        query_hash = self._hash_query(query)
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Eski kayıtları temizle
        cutoff = (datetime.now() - timedelta(hours=max_age_hours)).isoformat()
        cursor.execute("DELETE FROM query_cache WHERE created_at < ?", (cutoff,))
        
        # Cache'den getir
        row = cursor.execute("""
            SELECT response FROM query_cache 
            WHERE query_hash = ? AND created_at >= ?
        """, (query_hash, cutoff)).fetchone()
        
        if row:
            # Hit count güncelle
            cursor.execute("""
                UPDATE query_cache 
                SET hit_count = hit_count + 1, last_hit_at = ?
                WHERE query_hash = ?
            """, (datetime.now().isoformat(), query_hash))
            conn.commit()
            conn.close()
            return row[0]
        
        conn.close()
        return None
    
    def set(self, query: str, response: str, model_type: str = "unknown"):
        """Yanıtı cache'e kaydet"""
        query_hash = self._hash_query(query)
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO query_cache 
            (query_hash, query_text, response, model_type, created_at, last_hit_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            query_hash,
            query,
            response,
            model_type,
            datetime.now().isoformat(),
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def clear(self):
        """Tüm cache'i temizle"""
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("DELETE FROM query_cache")
        conn.commit()
        conn.close()
    
    def get_stats(self) -> dict:
        """Cache istatistikleri"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        total = cursor.execute("SELECT COUNT(*) FROM query_cache").fetchone()[0]
        total_hits = cursor.execute("SELECT SUM(hit_count) FROM query_cache").fetchone()[0] or 0
        
        conn.close()
        
        return {
            "total_cached": total,
            "total_hits": total_hits,
            "hit_rate": (total_hits / max(total, 1)) if total > 0 else 0
        }

# Global instance
_cache = None

def get_cache() -> QueryCache:
    """Singleton cache"""
    global _cache
    if _cache is None:
        _cache = QueryCache()
    return _cache
