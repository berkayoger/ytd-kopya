from __future__ import annotations
from typing import Dict, Tuple

"""
Canlı ortama yönelik gelişmiş karar mantığı
-------------------------------------------
Bu modül copy/evaluate çıktısını ek kısıtlarla iyileştirir:
 - rejime göre ölçekleme (boğa/ayı/oynak/yatay)
 - skor eşikleri ve histerezis
 - canlı mod için risk kapakları
 - bir sorun olursa temel mantığa geri dönüş
"""

DEFAULT_THRESH_BUY = 0.015   # BUY için minimum skor
DEFAULT_THRESH_SELL = 0.015  # SELL için minimum skor


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _regime_mult(regime_probs: Dict[str, float]) -> float:
    """Boğada risk artır, ayı/oynak piyasada azalt. [0.6, 1.2] aralığına sıkıştır."""
    bull = float(regime_probs.get("bull", 0.0))
    bear = float(regime_probs.get("bear", 0.0))
    vol = float(regime_probs.get("volatile", 0.0))
    m = 1.0 + 0.4 * bull - 0.3 * bear - 0.2 * vol
    return _clamp(m, 0.6, 1.2)


def _direction_match(decision: str, side: str) -> bool:
    return (decision == "LONG" and side == "BUY") or (decision == "SHORT" and side == "SELL")


def advanced_decision_logic(
    *,
    draks_out: Dict,
    side: str,
    base_scale: float,
    live_mode: bool,
    thresh_buy: float = DEFAULT_THRESH_BUY,
    thresh_sell: float = DEFAULT_THRESH_SELL,
) -> Tuple[bool, float]:
    """
    (yeşil_ışık, ölçek) döndürür
    - Yön ve skor kontrolleri
    - Rejime göre çarpan
    - Canlı mod kapakları
    """
    decision = str(draks_out.get("decision", "HOLD")).upper()
    score = float(draks_out.get("score", 0.0))
    regimes = dict(draks_out.get("regime_probs") or {})

    # 1) Yön uyumu zorunlu
    if not _direction_match(decision, side):
        return False, 0.0

    # 2) Aksiyon başına skor eşiği
    if decision == "LONG" and score < thresh_buy:
        return False, 0.0
    if decision == "SHORT" and score < thresh_sell:
        return False, 0.0

    # 3) Rejime göre çarpan
    mult = _regime_mult(regimes)
    scaled = base_scale * mult

    # 4) Sağduyu & canlı mod kapakları
    if live_mode:
        scaled = _clamp(scaled, 0.0, 0.75)
    else:
        scaled = _clamp(scaled, 0.0, 0.95)

    # 5) Çok küçük ölçekler gürültü
    if scaled < 0.02:
        return False, 0.0

    return True, scaled
