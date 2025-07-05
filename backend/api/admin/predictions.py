from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from backend.auth.middlewares import admin_required
from backend.db import db
from backend.db.models import PredictionOpportunity
from datetime import datetime

# Admin paneli tahmin yönetimi için Blueprint tanımı
predictions_bp = Blueprint("predictions", __name__, url_prefix="/api/admin/predictions")


@predictions_bp.route("/", methods=["GET"])
@jwt_required()
@admin_required()
def list_predictions():
    """Tüm tahmin fırsatlarını en yeniden eskiye doğru listeler."""
    predictions = PredictionOpportunity.query.order_by(PredictionOpportunity.created_at.desc()).all()
    return jsonify([p.to_dict() for p in predictions])


@predictions_bp.route("/", methods=["POST"])
@jwt_required()
@admin_required()
def create_prediction():
    """Yeni bir tahmin fırsatı oluşturur."""
    data = request.get_json() or {}
    try:
        # Gerekli alanların varlığını kontrol et
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
            created_at=datetime.utcnow(),
        )
        db.session.add(pred)
        db.session.commit()
        return jsonify(pred.to_dict()), 201
    except ValueError as ve:
        # Sayısal alanlara yanlış tipte veri girilirse hata yakala
        return jsonify({"error": f"Tip uyuşmazlığı: Lütfen sayısal alanlara geçerli bir değer girin. Detay: {str(ve)}"}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400


@predictions_bp.route("/<int:prediction_id>", methods=["PATCH"])
@jwt_required()
@admin_required()
def update_prediction(prediction_id):
    """Mevcut bir tahmin fırsatını kısmen günceller."""
    data = request.get_json() or {}
    pred = PredictionOpportunity.query.get_or_404(prediction_id)

    try:
        # Alan listeleri
        float_fields = ["current_price", "target_price", "expected_gain_pct", "confidence_score"]
        all_fields = [
            "symbol", "current_price", "target_price", "forecast_horizon",
            "expected_gain_pct", "confidence_score", "trend_type", 
            "source_model", "is_active"
        ]

        for field in all_fields:
            if field in data:
                value = data[field]
                if field in float_fields:
                    setattr(pred, field, float(value))
                elif field == "symbol":
                    setattr(pred, field, value.upper())
                else:
                    setattr(pred, field, value)

        db.session.commit()
        return jsonify(pred.to_dict()), 200
    except ValueError as ve:
        # Sayısal alanlara yanlış tipte veri girilirse hata yakala
        return jsonify({"error": f"Tip uyuşmazlığı: Lütfen sayısal alanlara geçerli bir değer girin. Detay: {str(ve)}"}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400


@predictions_bp.route("/<int:prediction_id>", methods=["DELETE"])
@jwt_required()
@admin_required()
def delete_prediction(prediction_id):
    """Bir tahmin fırsatını siler."""
    pred = PredictionOpportunity.query.get_or_404(prediction_id)
    db.session.delete(pred)
    db.session.commit()
    return jsonify({"message": "Tahmin fırsatı başarıyla silindi."}), 200


# Veri Toplama Planı (Düşük maliyetli güvenilir kaynaklar)
# Bu veri kaynakları ileride tahmin motoruna beslenecek

DATA_SOURCES = [
    {"type": "Fiyat/Grafik", "source": "CoinGecko API", "reliability": "High", "cost": "Free", "python_tool": "pycoingecko"},
    {"type": "Teknik Analiz", "source": "Kendin Hesapla", "reliability": "High", "cost": "Free", "python_tool": "pandas-ta"},
    {"type": "Haberler", "source": "RSS Beslemeleri", "reliability": "Mid-High", "cost": "Free", "python_tool": "feedparser"},
    {"type": "Haberler (Alternatif)", "source": "NewsAPI.org", "reliability": "High", "cost": "Free Tier", "python_tool": "requests"},
    {"type": "Haber & Yorum", "source": "CryptoPanic API", "reliability": "Mid-High", "cost": "Free Tier", "python_tool": "requests"},
    {"type": "Sosyal Etki", "source": "LunarCrush API", "reliability": "Mid", "cost": "Free Tier", "python_tool": "requests"},
    {"type": "Etkinlik Takvimi", "source": "CoinMarketCal", "reliability": "Mid", "cost": "Free", "python_tool": "requests"},
    {"type": "Yorum & Söylem", "source": "Messari News", "reliability": "High", "cost": "Free Tier", "python_tool": "requests"},
    {"type": "Haber", "source": "CoinTelegraph RSS", "reliability": "High", "cost": "Free", "python_tool": "feedparser"}
]

# Planlanan veri toplama görevleri (fonksiyon adları ve açıklamaları ile birlikte tanımlanacak)
# Bu fonksiyonlar ayrı görev dosyalarında zamanlanmış görevler olarak çalıştırılacaktır

# - fetch_price_data()      -> CoinGecko üzerinden fiyat verilerini alır
# - fetch_technical_data()  -> Teknik analiz verilerini üretir
# - fetch_news_rss()        -> RSS kaynaklarından haberleri çeker
# - fetch_news_api()        -> NewsAPI ve CryptoPanic gibi API'lerden haberleri toplar
# - fetch_social_signals()  -> LunarCrush gibi kaynaklardan sosyal etki sinyalleri çeker
# - fetch_event_calendar()  -> CoinMarketCal'den yaklaşan etkinlikleri alır
# - fetch_sentiment_news()  -> Messari gibi kaynaklardan yorumlu haberleri çeker


def fetch_price_data(symbol: str, vs_currency: str = "usd") -> dict:
    """CoinGecko API üzerinden fiyat verilerini döndürür."""
    import requests

    try:
        resp = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": symbol, "vs_currencies": vs_currency},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json().get(symbol, {})
    except Exception:  # pragma: no cover - dış servis hatası
        return {}


def fetch_technical_data(prices: list[float]) -> dict:
    """Basit teknik analiz indikatörlerini hesaplar (pandas-ta)."""
    try:  # pragma: no cover - isteğe bağlı kütüphane
        import pandas as pd
        import pandas_ta as ta
    except Exception:
        return {}

    if not prices:
        return {}

    df = pd.DataFrame(prices, columns=["close"])
    indicators = {
        "rsi": ta.rsi(df["close"]).iloc[-1],
        "macd": ta.macd(df["close"])["MACD_12_26_9"].iloc[-1],
    }
    return {k: float(v) for k, v in indicators.items() if v is not None}


def fetch_news_rss(urls: list[str]) -> list[dict]:
    """RSS kaynaklarından haber başlıklarını döndürür."""
    try:  # pragma: no cover - isteğe bağlı kütüphane
        import feedparser
    except Exception:
        return []

    articles: list[dict] = []
    for url in urls:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            articles.append({
                "title": entry.get("title"),
                "link": entry.get("link"),
            })
    return articles


def fetch_news_api(api_key: str, query: str, page_size: int = 10) -> list[dict]:
    """NewsAPI üzerinden haberleri alır."""
    import requests

    try:
        resp = requests.get(
            "https://newsapi.org/v2/everything",
            params={"q": query, "apiKey": api_key, "pageSize": page_size},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json().get("articles", [])
    except Exception:  # pragma: no cover - dış servis hatası
        return []


def fetch_social_signals(symbol: str, api_key: str | None = None) -> dict:
    """LunarCrush API üzerinden sosyal sinyal verisi toplar."""
    import requests

    params = {"data": "assets", "symbol": symbol}
    if api_key:
        params["key"] = api_key
    try:
        resp = requests.get("https://api.lunarcrush.com/v2", params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return data.get("data", [{}])[0] if data.get("data") else {}
    except Exception:  # pragma: no cover - dış servis hatası
        return {}


def fetch_event_calendar(api_key: str, symbol: str) -> list[dict]:
    """CoinMarketCal API'inden yaklaşan etkinlikleri getirir."""
    import requests

    headers = {"x-api-key": api_key}
    try:
        resp = requests.get(
            "https://developers.coinmarketcal.com/v1/events",
            params={"symbols": symbol},
            headers=headers,
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json().get("body", [])
    except Exception:  # pragma: no cover - dış servis hatası
        return []


def fetch_sentiment_news(api_key: str, asset: str) -> list[dict]:
    """Messari News API'den duygu analizi yapılmış haberleri döndürür."""
    import requests

    try:
        resp = requests.get(
            "https://data.messari.io/api/v1/news",
            params={"assets": asset},
            headers={"x-messari-api-key": api_key},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json().get("data", [])
    except Exception:  # pragma: no cover - dış servis hatası
        return []

