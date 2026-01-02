import sqlite3
from pathlib import Path

DEFAULT_DB_PATH = Path("data/spendrag.sqlite")

def connect(db_path: Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn

def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS receipts (
      id TEXT PRIMARY KEY,
      source_path TEXT NOT NULL,
      raw_text_hash TEXT NOT NULL UNIQUE,
      raw_text TEXT NOT NULL,

      merchant TEXT,
      receipt_date TEXT,
      currency TEXT DEFAULT 'TRY',
      total_amount REAL
    );

    CREATE TABLE IF NOT EXISTS items (
      id TEXT PRIMARY KEY,
      receipt_id TEXT NOT NULL,

      name_raw TEXT NOT NULL,
      name_norm TEXT,
      qty REAL,
      unit TEXT,
      amount REAL,
      category TEXT,

      line_no INTEGER,
      evidence_snippet TEXT,

      FOREIGN KEY(receipt_id) REFERENCES receipts(id)
    );
    """)
    conn.commit()
