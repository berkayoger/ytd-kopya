from __future__ import annotations

import random
import pandas as pd
from flask import Blueprint, jsonify, request, g
from flask_limiter.util import get_remote_address

from backend import limiter
from backend.utils.feature_flags import feature_flag_enabled
from backend.utils.logger import create_log

predict_bp = Blueprint("predict", __name__)


def fetch_price_data() -> pd.DataFrame:
    """Return a simple DataFrame of placeholder symbols.

    This avoids external API calls while providing sample data for
    recommendations.
    """
    symbols = [
        "BTC",
        "ETH",
        "XRP",
        "LTC",
        "ADA",
        "SOL",
        "BNB",
        "DOT",
        "DOGE",
        "AVAX",
    ]
    return pd.DataFrame({"symbol": symbols})


@predict_bp.route("/recommend", methods=["POST"])
@limiter.limit("5 per minute", key_func=get_remote_address)
def recommend_stocks():
    """Return a set of randomly selected coin symbols.

    Feature flag ``recommendation_enabled`` must be enabled for the
    endpoint to serve data.
    """
    if not feature_flag_enabled("recommendation_enabled"):
        return jsonify({"error": "Özellik şu anda devre dışı."}), 403

    user = g.get("user")
    ip_address = request.remote_addr or "unknown"
    user_agent = request.headers.get("User-Agent", "")

    try:
        df = fetch_price_data()
        symbols = df["symbol"].unique().tolist()
        selected = random.sample(symbols, k=min(5, len(symbols)))
        return jsonify({"recommendations": selected})
    except Exception as e:  # pragma: no cover - defensive
        return jsonify({"error": str(e)}), 500
    finally:
        if user:
            create_log(
                user_id=str(user.id),
                username=user.username,
                ip_address=ip_address,
                action="recommend",
                target="/api/recommend",
                description="Öneri tahmini yapıldı.",
                status="success",
                user_agent=user_agent,
            )
