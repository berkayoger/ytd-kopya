from backend.db.models import TechnicalIndicator
from sqlalchemy import desc


def generate_ta_based_recommendation(symbol="bitcoin"):
    indicator = (
        TechnicalIndicator.query.filter_by(symbol=symbol.upper())
        .order_by(desc(TechnicalIndicator.created_at))
        .first()
    )
    if not indicator:
        return None

    recommendation = []
    if indicator.rsi is not None:
        if indicator.rsi < 30:
            recommendation.append("RSI çok düşük → Aşırı satım bölgesi")
        elif indicator.rsi > 70:
            recommendation.append("RSI çok yüksek → Aşırı alım bölgesi")

    if indicator.macd is not None and indicator.signal is not None:
        if indicator.macd > indicator.signal:
            recommendation.append("MACD > Signal → Al sinyali")
        else:
            recommendation.append("MACD < Signal → Sat sinyali")

    return {
        "symbol": symbol.upper(),
        "rsi": round(indicator.rsi, 2) if indicator.rsi is not None else None,
        "macd": round(indicator.macd, 2) if indicator.macd is not None else None,
        "signal": round(indicator.signal, 2) if indicator.signal is not None else None,
        "created_at": indicator.created_at.isoformat(),
        "insight": recommendation,
    }
