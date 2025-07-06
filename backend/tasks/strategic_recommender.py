from backend.db.models import TechnicalIndicator
from sqlalchemy import desc
from backend.engine.strategic_decision_engine import advanced_decision_logic


def generate_ta_based_recommendation(symbol="bitcoin"):
    """Create a recommendation using the advanced decision engine."""
    indicator = (
        TechnicalIndicator.query.filter_by(symbol=symbol.upper())
        .order_by(desc(TechnicalIndicator.created_at))
        .first()
    )
    if not indicator:
        return None

    indicators = {
        "rsi": indicator.rsi,
        "macd": indicator.macd,
        "macd_signal": indicator.signal,
        "price": None,  # Can be filled with live price data
        "sma_10": None,
        "prev_predictions_success_rate": 0.75,
    }

    decision = advanced_decision_logic(indicators)
    if decision["signal"] == "avoid":
        return None

    return {
        "symbol": symbol.upper(),
        "rsi": indicator.rsi,
        "macd": indicator.macd,
        "signal": indicator.signal,
        "insight": decision,
        "created_at": indicator.created_at.isoformat(),
    }
