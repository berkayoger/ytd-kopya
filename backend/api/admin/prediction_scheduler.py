from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from backend.auth.middlewares import admin_required
from backend.db import db
from backend.db.models import PredictionOpportunity
from datetime import datetime
from backend.utils.helpers import add_audit_log
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from pycoingecko import CoinGeckoAPI
import pandas_ta as ta
import feedparser
import requests

predictions_bp = Blueprint("predictions", __name__, url_prefix="/api/admin/predictions")
logger = logging.getLogger(__name__)


@predictions_bp.route("/", methods=["GET"])
@jwt_required()
@admin_required()
def list_predictions():
    predictions = PredictionOpportunity.query.order_by(PredictionOpportunity.created_at.desc()).all()
    return jsonify([p.to_dict() for p in predictions])


@predictions_bp.route("/", methods=["POST"])
@jwt_required()
@admin_required()
def create_prediction():
    data = request.get_json() or {}
    try:
        required_fields = ["symbol", "current_price", "target_price", "expected_gain_pct"]
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"'{field}' alanı zorunludur"}), 400

        pred = PredictionOpportunity(
            symbol=data["symbol"].upper(),
            current_price=float(data["current_price"]),
            target_price=float(data["target_price"]),
            forecast_horizon=data.get("forecast_horizon"),
            expected_gain_pct=float(data["expected_gain_pct"]),
            confidence_score=float(data.get("confidence_score", 0.0)),
            trend_type=data.get("trend_type", "short_term"),
            source_model=data.get("source_model", "AIModel"),
            is_active=bool(data.get("is_active", True)),
            created_at=datetime.utcnow()
        )
        db.session.add(pred)
        db.session.commit()
        add_audit_log(action_type="prediction_created", details={"symbol": pred.symbol})
        return jsonify(pred.to_dict()), 201
    except ValueError as ve:
        return jsonify({"error": f"Tip uyuşmazlığı: {str(ve)}"}), 400
    except Exception as e:
        db.session.rollback()
        logger.exception("Tahmin oluşturma hatası")
        return jsonify({"error": str(e)}), 400


@predictions_bp.route("/<int:prediction_id>", methods=["PATCH"])
@jwt_required()
@admin_required()
def update_prediction(prediction_id):
    data = request.get_json() or {}
    pred = PredictionOpportunity.query.get_or_404(prediction_id)
    try:
        float_fields = ["current_price", "target_price", "expected_gain_pct", "confidence_score"]
        for field in [
            "symbol", "current_price", "target_price", "forecast_horizon",
            "expected_gain_pct", "confidence_score", "trend_type", "source_model", "is_active"
        ]:
            if field in data:
                value = data[field]
                if field in float_fields:
                    setattr(pred, field, float(value))
                elif field == "symbol":
                    setattr(pred, field, value.upper())
                else:
                    setattr(pred, field, value)
        db.session.commit()
        add_audit_log(action_type="prediction_updated", target_id=prediction_id, details=data)
        return jsonify(pred.to_dict()), 200
    except ValueError as ve:
        return jsonify({"error": f"Tip uyuşmazlığı: {str(ve)}"}), 400
    except Exception as e:
        db.session.rollback()
        logger.exception("Tahmin güncelleme hatası")
        return jsonify({"error": str(e)}), 400


@predictions_bp.route("/<int:prediction_id>", methods=["DELETE"])
@jwt_required()
@admin_required()
def delete_prediction(prediction_id):
    pred = PredictionOpportunity.query.get_or_404(prediction_id)
    db.session.delete(pred)
    db.session.commit()
    add_audit_log(action_type="prediction_deleted", target_id=prediction_id, details={"symbol": pred.symbol})
    return jsonify({"message": "Silindi"}), 200


# Veri Toplama
cg = CoinGeckoAPI()


def fetch_price_data():
    logger.info("[TASK] CoinGecko veri toplama başlatıldı")
    try:
        data = cg.get_price(ids='bitcoin,ethereum', vs_currencies='usd')
        logger.info(f"[DATA] Fiyat verisi: {data}")
    except Exception as e:
        logger.error(f"[ERROR] CoinGecko API hatası: {e}")


def fetch_technical_data():
    logger.info("[TASK] Teknik analiz hesaplama başlatıldı")
    import pandas as pd
    df = pd.DataFrame({'close': [100, 102, 101, 105, 110]})
    rsi = ta.rsi(df['close'])
    logger.info(f"[DATA] RSI verisi: {rsi.dropna().to_list()}")


def fetch_news_rss():
    logger.info("[TASK] RSS haber toplama başlatıldı")
    feed = feedparser.parse('https://cointelegraph.com/rss')
    for entry in feed.entries[:3]:
        logger.info(f"[NEWS] {entry.title}")


def fetch_news_api():
    logger.info("[TASK] NewsAPI verisi çekiliyor")
    try:
        url = "https://newsapi.org/v2/everything?q=crypto&apiKey=demo"
        res = requests.get(url)
        if res.ok:
            articles = res.json().get("articles", [])
            for a in articles[:3]:
                logger.info(f"[API NEWS] {a['title']}")
    except Exception as e:
        logger.error(f"[ERROR] NewsAPI: {e}")


def fetch_social_signals():
    logger.info("[TASK] Sosyal sinyal verisi toplanıyor (placeholder)")


def fetch_event_calendar():
    logger.info("[TASK] CoinMarketCal etkinlik kontrolü (placeholder)")


def fetch_sentiment_news():
    logger.info("[TASK] Messari haber taraması (placeholder)")


scheduler = BackgroundScheduler(daemon=True)
scheduler.add_job(fetch_price_data, 'interval', minutes=15, id="price_task")
scheduler.add_job(fetch_technical_data, 'interval', hours=1, id="tech_task")
scheduler.add_job(fetch_news_rss, 'interval', minutes=30, id="rss_task")
scheduler.add_job(fetch_news_api, 'interval', hours=2, id="news_task")
scheduler.add_job(fetch_social_signals, 'interval', hours=3, id="social_task")
scheduler.add_job(fetch_event_calendar, 'interval', hours=6, id="event_task")
scheduler.add_job(fetch_sentiment_news, 'interval', hours=4, id="sentiment_task")
scheduler.start()
