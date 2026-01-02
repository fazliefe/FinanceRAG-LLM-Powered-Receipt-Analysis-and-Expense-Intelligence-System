from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class Rule:
    category: str
    keywords: tuple[str, ...]

# MVP kural seti (genişletilebilir)
RULES: list[Rule] = [
    Rule("gida", ("sut", "yogurt", "ekmek", "yumurta", "domates", "makarna", "pirinc", "un", "seker", "tuz", "peynir")),
    Rule("temizlik", ("bulasik", "deterjan", "camasir", "yumusatici", "camasir suyu", "dezenfektan", "sabun")),
    Rule("su_icecek", ("su ", "maden suyu", "kola", "ayran", "meyve suyu", "soda")),
    Rule("kisisel_bakim", ("sampuan", "dis macunu", "dis fircasi", "deodorant", "ped", "tisort", "kolonya")),
    Rule("ev", ("ampul", "pil", "poset", "strech", "folyo", "kagit havlu", "pecete", "tuvalet kagidi")),
]

def categorize(norm_name: str) -> str:
    x = (norm_name or "").strip()
    if not x:
        return "diger"

    # basit keyword eşleme
    for rule in RULES:
        for kw in rule.keywords:
            if kw in x:
                return rule.category

    return "diger"
