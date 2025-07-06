from datetime import datetime, timedelta
import logging

from pycoingecko import CoinGeckoAPI

from backend.tasks.strategic_recommender import generate_ta_based_recommendation
from backend.utils.price_fetcher import fetch_current_price
from backend.db import db
from backend.db.models import PredictionOpportunity

logger = logging.getLogger(__name__)
cg = CoinGeckoAPI()


def generate_predictions_for_all_coins(limit: int = 5):
    """Generate TA-based predictions for the most popular coins."""
    try:
        coins = cg.get_coins_markets(vs_currency="usd", per_page=limit, page=1)
        symbols = [coin["id"] for coin in coins]

        created: list[str] = []
        for sym in symbols:
            data = generate_ta_based_recommendation(symbol=sym)
            if not data:
                continue
            current_price = fetch_current_price(sym)
            if current_price is None:
                continue
            pred = PredictionOpportunity(
                symbol=data["symbol"],
                current_price=current_price,
                target_price=round(current_price * 1.03, 2),
                expected_gain_pct=3.0,
                confidence_score=85,
                trend_type="short_term",
                source_model="TA-Strategy",
                is_active=True,
                is_public=True,
                forecast_horizon="1d",
                created_at=datetime.utcnow(),
            )
            db.session.add(pred)
            created.append(data["symbol"])
        db.session.commit()
        logger.info(f"[TA-BULK] Otomatik tahminler üretildi: {created}")
        return created
    except Exception as e:  # pragma: no cover - just log errors
        logger.error(f"[TA-BULK] Tahmin üretim hatası: {e}")
        return []
