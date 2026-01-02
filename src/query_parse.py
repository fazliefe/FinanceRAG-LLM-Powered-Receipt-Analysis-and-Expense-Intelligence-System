from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional

CATEGORY_ALIASES = {
    "gida": ["gida", "yemek", "market", "mutfak"],
    "temizlik": ["temizlik", "deterjan", "bulasik", "camasir"],
    "su_icecek": ["su", "icecek", "içecek", "soda", "maden suyu"],
    "kisisel_bakim": ["kisisel", "bakim", "kişisel", "sampuan", "şampuan", "dis macunu"],
    "ev": ["ev", "ampul", "pil", "kagit", "kağıt"],
}

STOPWORDS = {
    "kac", "kaç", "lira", "tutar", "toplam", "harcama", "harcamam", "ne", "nedir",
    "mi", "mı", "mu", "mü", "son", "gun", "gün", "ay", "bu", "gecen", "geçen",
    "kategorilere", "dagilim", "dağılım", "kırılım", "kirilim",
    "en", "cok", "çok", "kez", "defa", "adet", "tane", "alinmis", "alınmış"
}

@dataclass
class QuerySpec:
    product_term: Optional[str] = None
    category: Optional[str] = None
    date_from: Optional[str] = None  # YYYY-MM-DD
    date_to: Optional[str] = None    # YYYY-MM-DD (inclusive)

def _iso(d: date) -> str:
    return d.isoformat()

def parse_query(q: str) -> QuerySpec:
    x = (q or "").strip().lower()
    spec = QuerySpec()

    # 1) Kategori (substring)
    for cat, keys in CATEGORY_ALIASES.items():
        if any(k in x for k in keys):
            spec.category = cat
            break

    # 2) Tarih filtreleri
    today = date.today()

    m = re.search(r"son\s+(\d+)\s+g[uü]n", x)
    if m:
        n = int(m.group(1))
        spec.date_from = _iso(today - timedelta(days=n))
        spec.date_to = _iso(today)

    m = re.search(r"(20\d{2})[-/](\d{1,2})", x)
    if m:
        y = int(m.group(1)); mo = int(m.group(2))
        start = date(y, mo, 1)
        if mo == 12:
            end = date(y + 1, 1, 1) - timedelta(days=1)
        else:
            end = date(y, mo + 1, 1) - timedelta(days=1)
        spec.date_from = _iso(start)
        spec.date_to = _iso(end)

    if "bu ay" in x:
        start = date(today.year, today.month, 1)
        spec.date_from = _iso(start)
        spec.date_to = _iso(today)

    if ("gecen ay" in x) or ("geçen ay" in x):
        first_this = date(today.year, today.month, 1)
        end = first_this - timedelta(days=1)
        start = date(end.year, end.month, 1)
        spec.date_from = _iso(start)
        spec.date_to = _iso(end)

    # 3) Ürün terimi
    # 3.a) Özel durum: "su" 2 harf ama çok kritik; token olarak varsa product_term="su"
    if re.search(r"\bsu\b", x):
        spec.product_term = "su"
        return spec

    # 3.b) Genel durum: 3+ harfli adaylardan ilkini seç
    tokens = re.findall(r"[A-Za-zÇĞİÖŞÜçğıöşü]{3,}", q)
    candidates = []
    for t in tokens:
        tl = t.lower()
        if tl in STOPWORDS:
            continue
        # kategori kelimelerini ele
        if any(tl in keys for keys in CATEGORY_ALIASES.values()):
            continue
        candidates.append(t)

    if candidates:
        spec.product_term = candidates[0]

    return spec
