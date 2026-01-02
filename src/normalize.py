import re

_TR_MAP = str.maketrans({
    "ı": "i", "İ": "i",
    "ş": "s", "Ş": "s",
    "ğ": "g", "Ğ": "g",
    "ü": "u", "Ü": "u",
    "ö": "o", "Ö": "o",
    "ç": "c", "Ç": "c",
})

def normalize_name(s: str) -> str:
    """
    Ürün adını arama/analiz için normalize eder.
    - küçük harf
    - TR karakterlerini sadeleştirir (opsiyonel ama aramada işe yarar)
    - noktalama/kod gürültüsünü azaltır
    - fazla boşlukları tekleştirir
    """
    if not s:
        return ""
    x = s.strip()
    x = x.casefold()
    x = x.translate(_TR_MAP)

    # Birim/format küçük düzenlemeler
    x = x.replace("lt", "l").replace("l t", "l")
    x = x.replace("kg", "kg").replace("gr", "g")

    # Alfasayısal + boşluk dışındakileri boşluğa çevir
    x = re.sub(r"[^a-z0-9\s\.\-]", " ", x)
    x = re.sub(r"\s+", " ", x).strip()
    return x
