def extract_features(data: dict) -> dict:
    """
    Girdi verisinden teknik ve haber göstergelerini çıkarır.
    :param data: coin'e ait ham veriler (örnek: RSI, MACD, haber skoru)
    :return: normalize edilmiş feature dict
    """
    return {
        "rsi": float(data.get("rsi", 0)),
        "macd_signal_diff": float(data.get("macd", 0))
        - float(data.get("macd_signal", 0)),
        "sma_trend": float(data.get("sma_7", 0)) - float(data.get("sma_30", 0)),
        "prev_success_rate": float(data.get("prev_success_rate", 0)),
        "sentiment_score": float(data.get("sentiment_score", 0)),
        "news_count": int(data.get("news_count", 0)),
    }
