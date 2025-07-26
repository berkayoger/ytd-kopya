def calculate_score(features: dict) -> float:
    """Normalize edilmiş özniteliklere göre ağırlıklı skor hesaplar."""
    weights = {
        "rsi": 0.2,
        "macd_signal_diff": 0.25,
        "sma_trend": 0.2,
        "prev_success_rate": 0.15,
        "sentiment_score": 0.15,
        "news_count": 0.05,
    }
    score = 0.0
    for key, weight in weights.items():
        score += features.get(key, 0) * weight
    return min(max(score, 0), 100)
