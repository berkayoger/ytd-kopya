# backend/api/routes.py

import json

import requests
from flask import Blueprint, current_app, g, jsonify, request

try:
    from flask_limiter import current_limiter as limiter
except ImportError:  # Eski Flask-Limiter sürümleri için geri dönüş
    from backend import limiter  # pragma: no cover

import html
import time  # For time.time()
from datetime import date, datetime, timedelta

from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_limiter.errors import RateLimitExceeded
from loguru import logger
from sqlalchemy.exc import IntegrityError

from backend.auth.middlewares import admin_required
from backend.constants import SUBSCRIPTION_EXTENSION_DAYS
# Modelleri import et
from backend.db.models import (DailyUsage, PromoCode, PromoCodeUsage,
                               SecurityEvent, SubscriptionPlan, User, db)
from backend.db.secure_queries import SecureQueryManager
from backend.limiting import get_plan_rate_limit, rate_limit_key_func
from backend.middleware.plan_limits import enforce_plan_limit
# Güvenlik dekoratörlerini import et
from backend.utils.decorators import require_subscription_plan
# Yardımcı fonksiyonları import et
from backend.utils.helpers import add_audit_log, serialize_user_for_api
from backend.utils.logger import create_log
from backend.utils.plan_limits import get_all_feature_keys
from backend.utils.security import sanitize_input
from backend.utils.usage_limits import check_usage_limit, get_usage_status
from backend.utils.validators import validate_crypto_symbol
from backend.validation.schemas import (AdminAnalyticsRequestSchema,
                                        CryptoAnalysisRequestSchema)
from backend.validation.validators import validate_json

# API Blueprint'i tanımla
api_bp = Blueprint("api", __name__)


@api_bp.before_request
def security_headers() -> None:
    """Placeholder for request-level security logic."""
    return None


@api_bp.after_request
def add_security_headers(response):
    """Add basic security headers to each response."""
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = (
        "max-age=31536000; includeSubDomains"
    )
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    return response


# Flask-Limiter aşımlarında tek tip JSON cevap ver
@api_bp.errorhandler(RateLimitExceeded)
def _handle_rl_exceeded(e):
    try:
        retry_after = getattr(e, "retry_after", None)
    except Exception:
        retry_after = None
    payload = {"error": "RateLimitExceeded", "message": "Too Many Requests"}
    resp = jsonify(payload)
    if retry_after is not None:
        resp.headers["Retry-After"] = str(retry_after)
    return resp, 429


# Plan değişikliği için kullanıcı başına ek Redis limit sabitleri
PLAN_UPDATE_LIMIT_PER_MINUTE = 1  # 60 saniyede maksimum 1 plan güncelleme denemesi
PLAN_UPDATE_WINDOW_SECONDS = 60  # Pencere süresi (saniye)
MAX_SUBSCRIPTION_EXTENSION_DAYS = (
    5 * 365
)  # Promosyonlarla uzatılabilecek maksimum gün (örn. 5 yıl)

# Backend tarafından doğrulanacak plan fiyatları (Üretimde AdminSettings'ten veya başka güvenli bir kaynaktan gelmeli)
# Frontend'den gelen fiyat bilgisi ASLA doğrudan kullanılmamalıdır.
BACKEND_PLAN_PRICES = {
    SubscriptionPlan.BASIC.name: 9.99,
    SubscriptionPlan.ADVANCED.name: 24.99,
    SubscriptionPlan.PREMIUM.name: 49.99,
}


# ---------------------------------------------------------------------------
# Limit durumu (UI yardımcı)
# ---------------------------------------------------------------------------
@api_bp.route("/limits/status", methods=["GET"])
def limits_status():
    try:
        uid = str(get_jwt_identity())
        user = User.query.get(uid)
        if not user:
            return jsonify({"error": "User not found"}), 404
        feature_keys = get_all_feature_keys()
        status = {fk: get_usage_status(uid, fk) for fk in feature_keys}
        try:
            create_log(
                user_id=uid,
                username=user.username,
                ip_address=request.remote_addr or "unknown",
                action="limits_status",
                target="/api/limits/status",
                description="Kullanım limit durumu sorgulandı.",
                status="success",
                user_agent=request.headers.get("User-Agent", ""),
            )
        except Exception as log_err:
            logger.warning(f"limits_status log oluşturulamadı: {log_err}")
        return jsonify({"plan": str(user.subscription_level), "features": status}), 200
    except Exception as e:
        logger.error(f"limits_status error: {e}")
        return jsonify({"error": "Failed to fetch limit status"}), 500


# Analiz endpoint'i
@api_bp.route("/analyze_coin/<string:coin_id>", methods=["GET", "POST"])
# Rate limit: Kullanıcıya özel (API key bazlı) veya IP bazlı.
# rate limit aşıldığında 429 döner.
@limiter.limit(get_plan_rate_limit, key_func=rate_limit_key_func)
# Backend Guard: Minimum BASIC aboneliği gereklidir.
@require_subscription_plan(SubscriptionPlan.BASIC)
# Backend Guard: Günlük analiz çağrısı kotasını kontrol et.
@check_usage_limit("coin_analysis")
def analyze_coin_api(coin_id):
    user = g.user  # Dekorator'den gelen kullanıcı objesi

    # Kullanıcı girdisini XSS'e karşı temizle ve formatı doğrula
    coin_id = sanitize_input(coin_id or "").upper()
    if not validate_crypto_symbol(coin_id):
        logger.error("Geçersiz coin ID formatı isteği.")
        return jsonify({"error": "Geçersiz coin ID formatı."}), 400

    investor_profile = request.args.get("profile", "moderate").lower()
    if request.method == "POST":
        request_data = request.get_json(silent=True)
        if request_data and "profile" in request_data:
            investor_profile = request_data["profile"].lower()

    # Redis Cache Kontrolü
    r_client = current_app.extensions["redis_client"]
    # user.subscription_level string ya da enum olabilir - güvenli erişim
    plan_name = (
        getattr(user.subscription_level, "name", str(user.subscription_level))
        if hasattr(user, "subscription_level")
        else "basic"
    )
    cache_key = (
        f"analysis:{coin_id}:{investor_profile}:{plan_name}"  # Cache key'e plan eklendi
    )

    if r_client:
        cached_result = r_client.get(cache_key)
        if cached_result:
            logger.info(
                f"Cache'ten {coin_id.upper()} analizi servis ediliyor. Kullanıcı: {user.username}, Profil: {investor_profile}"
            )
            return jsonify(json.loads(cached_result))

    try:
        celery_app = current_app.extensions["celery"]

        priority = 5
        if user.subscription_level == SubscriptionPlan.PREMIUM:
            priority = 9
        elif user.subscription_level == SubscriptionPlan.ADVANCED:
            priority = 7

        task = celery_app.send_task(
            "backend.tasks.celery_tasks.analyze_coin_task",  # Celery görev yolu
            args=[coin_id, investor_profile, user.id],  # user.id eklendi
            kwargs={},
            options={"priority": priority},
        )
        logger.info(
            f"Celery: {coin_id.upper()} analizi görevi kuyruğa eklendi. Task ID: {task.id}. Kullanıcı: {user.username}"
        )

        if user:
            ip_address = request.remote_addr or "unknown"
            user_agent = request.headers.get("User-Agent", "")
            try:
                create_log(
                    user_id=str(user.id),
                    username=user.username,
                    ip_address=ip_address,
                    action="analyze_coin",
                    target=f"/api/analyze_coin/{coin_id}",
                    description=f"{coin_id.upper()} için analiz başlatıldı.",
                    status="success",
                    user_agent=user_agent,
                )
            except Exception as e:
                logger.warning(f"analyze_coin log oluşturulamadı: {e}")

        # Günlük kullanım kotasını atomik olarak artır
        with current_app.app_context():  # Ensure context for DB operations
            try:  # Transaction başlat
                daily_usage_record = DailyUsage.query.filter_by(
                    user_id=user.id, date=date.today()
                ).first()
                if not daily_usage_record:
                    daily_usage_record = DailyUsage(
                        user_id=user.id,
                        date=date.today(),
                        analyze_calls=0,
                        llm_queries=0,
                    )
                    db.session.add(daily_usage_record)
                    db.session.flush()  # Ensure ID is available for update() to work on new object

                # Atomik sayaç artırımı (race condition'ı önler)
                # synchronize_session=False, update sonrası session'daki objelerin güncellenmesini engeller.
                # refresh() ile sonra manuel olarak günceliyoruz.
                db.session.query(DailyUsage).filter_by(id=daily_usage_record.id).update(
                    {DailyUsage.analyze_calls: DailyUsage.analyze_calls + 1},
                    synchronize_session=False,
                )
                db.session.commit()  # DailyUsage artırımını commit et

                # Güncel kullanım sayısını almak için objeyi refresh et
                db.session.refresh(daily_usage_record)
                _u = g.get("user")
                _uname = (
                    getattr(_u, "username", None)
                    or getattr(_u, "email", None)
                    or getattr(_u, "id", "anonymous")
                )
                logger.info(
                    "Kullanıcı %s - Günlük analiz kullanımı: %s",
                    _uname,
                    getattr(daily_usage_record, "analyze_calls", "?"),
                )

                # Audit log kaydı
                add_audit_log(
                    action_type="COIN_ANALYSIS_REQUESTED",
                    actor_id=user.id,
                    actor_username=user.username,
                    target_id=None,
                    target_username=coin_id.upper(),
                    details={
                        "profile": investor_profile,
                        "ip_address": request.remote_addr,
                        "current_usage": daily_usage_record.analyze_calls,
                    },
                    ip_address=request.remote_addr,
                    commit=True,  # add_audit_log kendi commitini yapar
                )
            except Exception as db_e:
                db.session.rollback()  # Hata durumunda rollback yap
                logger.error(
                    f"DailyUsage artırılırken DB hatası: {db_e}. Kullanıcı: {user.username}"
                )
                # Hata durumunda alarma da devret
                raise  # Hatayı dışarı fırlat ki ana try-except yakalayabilsin

        return (
            jsonify(
                {
                    "status": "Analiz arka planda başlatıldı.",
                    "task_id": task.id,
                    "coin": coin_id,
                }
            ),
            202,
        )

    except requests.exceptions.RequestException as e:
        logger.error(f"Harici API bağlantı hatası: {e}. Kullanıcı: {user.username}")
        return (
            jsonify(
                {
                    "error": "Harici API bağlantı hatası. Lütfen daha sonra tekrar deneyin."
                }
            ),
            503,
        )
    except Exception as e:
        _u = g.get("user")
        _uname = (
            getattr(_u, "username", None)
            or getattr(_u, "email", None)
            or getattr(_u, "id", "anonymous")
        )
        logger.exception(
            "Analiz sırasında beklenmeyen bir hata oluştu: %s; Kullanıcı: %s", e, _uname
        )
        return jsonify({"error": "Bilinmeyen bir hata oluştu."}), 500


# LLM Destekli Analiz Endpoint'i (Sadece Premium Kullanıcılar İçin)
@api_bp.route("/llm/analyze", methods=["POST"])
@limiter.limit(get_plan_rate_limit, key_func=rate_limit_key_func)
@require_subscription_plan(SubscriptionPlan.PREMIUM)  # LLM için Premium plan
@check_usage_limit("llm_analyze")
def llm_analyze():
    user = g.user  # Dekorator'den gelen kullanıcı objesi
    prompt = request.json.get("prompt")
    if not prompt:
        return jsonify({"error": "Prompt eksik."}), 400

    simulated_result = f"LLM danışmanı yanıtı (PREMIUM erişim): '{prompt}' için piyasa çok olumlu görünüyor."
    logger.info(f"LLM analizi yapıldı. Kullanıcı: {user.username}")

    if user:
        ip_address = request.remote_addr or "unknown"
        user_agent = request.headers.get("User-Agent", "")
        try:
            create_log(
                user_id=str(user.id),
                username=user.username,
                ip_address=ip_address,
                action="llm_analyze",
                target="/api/llm/analyze",
                description="LLM ile analiz talebi yapıldı.",
                status="success",
                user_agent=user_agent,
            )
        except Exception as e:
            logger.warning(f"llm_analyze log oluşturulamadı: {e}")

    with current_app.app_context():
        try:
            daily_usage_record = DailyUsage.query.filter_by(
                user_id=user.id, date=date.today()
            ).first()
            if not daily_usage_record:
                daily_usage_record = DailyUsage(
                    user_id=user.id, date=date.today(), analyze_calls=0, llm_queries=0
                )
                db.session.add(daily_usage_record)
                db.session.flush()

            db.session.query(DailyUsage).filter_by(id=daily_usage_record.id).update(
                {DailyUsage.llm_queries: DailyUsage.llm_queries + 1},
                synchronize_session="fetch",
            )
            db.session.commit()  # DailyUsage artırımını commit et
            db.session.refresh(daily_usage_record)
            logger.info(
                f"Kullanıcı {user.username} - Günlük LLM kullanımı: {daily_usage_record.llm_queries}"
            )

            add_audit_log(
                action_type="LLM_QUERY",
                actor_id=user.id,
                actor_username=user.username,
                target_id=None,
                target_username=user.username,
                details={
                    "prompt_preview": prompt[:50],
                    "ip_address": request.remote_addr,
                    "current_usage": daily_usage_record.llm_queries,
                },
                ip_address=request.remote_addr,
                commit=True,
            )
        except Exception as db_e:
            db.session.rollback()  # Hata durumunda rollback yap
            logger.error(
                f"DailyUsage (LLM) artırılırken DB hatası: {db_e}. Kullanıcı: {user.username}"
            )
            raise  # Hatayı dışarı fırlat

    return jsonify({"result": simulated_result}), 200


# Basit demo tahmin endpoint'i plan limitleri ile korunur
@api_bp.route("/predict/", methods=["POST"])
@require_subscription_plan(SubscriptionPlan.TRIAL)
@enforce_plan_limit("prediction")
def predict():
    from backend.utils.usage_tracking import record_usage

    user = g.get("user")
    symbol = (request.get_json(silent=True) or {}).get("coin")
    if user:
        record_usage(user, "predict_daily")

        ip_address = request.remote_addr or "unknown"
        user_agent = request.headers.get("User-Agent", "")

        create_log(
            user_id=str(user.id),
            username=user.username,
            ip_address=ip_address,
            action="predict",
            target="/api/predict",
            description=(
                f"'{symbol}' için tahmin üretildi." if symbol else "Tahmin üretildi."
            ),
            status="success",
            user_agent=user_agent,
        )

    return jsonify({"result": "ok"}), 200


@api_bp.route("/predict/daily", methods=["POST"])
@jwt_required()
@enforce_plan_limit("predict_daily")
def daily_prediction():
    _ = request.json

    user = g.get("user")
    if user:
        ip_address = request.remote_addr or "unknown"
        user_agent = request.headers.get("User-Agent", "")
        try:
            create_log(
                user_id=str(user.id),
                username=user.username,
                ip_address=ip_address,
                action="predict_daily",
                target="/api/predict/daily",
                description="Günlük tahmin talebi yapıldı.",
                status="success",
                user_agent=user_agent,
            )
        except Exception as e:
            logger.warning(f"predict_daily log oluşturulamadı: {e}")

    return jsonify({"result": "daily"}), 200


# Basit çok günlü fiyat tahmini endpoint'i
@api_bp.route("/forecast/<string:coin_id>", methods=["GET"])
@limiter.limit(get_plan_rate_limit, key_func=rate_limit_key_func)
@require_subscription_plan(SubscriptionPlan.PREMIUM)
@check_usage_limit("forecast")
def forecast_coin(coin_id):
    """Return Prophet based forecast data for the requested coin."""
    user = g.user  # get user from decorator
    days_param = request.args.get("days", "1")
    try:
        days = int(days_param)
    except ValueError:
        return jsonify({"error": "days must be an integer"}), 400

    days = max(1, min(days, 30))

    # Loglama
    ip_address = request.remote_addr or "unknown"
    user_agent = request.headers.get("User-Agent", "")
    try:
        create_log(
            user_id=str(user.id),
            username=user.username,
            ip_address=ip_address,
            action="forecast",
            target=f"/api/forecast/{coin_id}",
            description=f"{coin_id.upper()} için {days} günlük tahmin istendi.",
            status="success",
            user_agent=user_agent,
        )
    except Exception as e:
        logger.warning(f"Forecast log oluşturulamadı: {e}")

    system = current_app.ytd_system_instance
    price_data = system.collector.collect_price_data(coin_id)
    (
        preds,
        method,
        bounds,
        dates,
        confidence,
        explanation,
    ) = system.ai.forecast(
        price_data["prices"],
        price_data["times"],
        days=days,
        coin_name=coin_id,
    )

    if preds is None:
        return jsonify({"error": "forecast unavailable"}), 503

    if days == 1:
        predictions = [preds]
        uppers = [bounds.get("upper")]
        lowers = [bounds.get("lower")]
        dates = dates[:1]
    else:
        predictions = preds
        uppers = bounds.get("upper")
        lowers = bounds.get("lower")

    forecast_data = []
    for i in range(len(predictions)):
        forecast_data.append(
            {
                "date": dates[i],
                "price": predictions[i],
                "upper": uppers[i],
                "lower": lowers[i],
            }
        )

    return (
        jsonify(
            {
                "coin": coin_id,
                "days": days,
                "forecast": forecast_data,
                "confidence": confidence,
                "explanation": explanation,
                "method": method,
            }
        ),
        200,
    )


# Gelişmiş teknik göstergeler endpoint'i
@api_bp.route("/technical_indicators/<string:coin_id>", methods=["GET"])
@limiter.limit(get_plan_rate_limit, key_func=rate_limit_key_func)
@require_subscription_plan(SubscriptionPlan.ADVANCED)
def technical_indicators(coin_id):
    """Return RSI, MACD and other indicators for the requested coin."""
    system = current_app.ytd_system_instance
    price_data = system.collector.collect_price_data(coin_id)
    return (
        jsonify(
            {
                "coin": coin_id,
                "rsi": price_data.get("rsi"),
                "macd": price_data.get("macd"),
                "bb_upper": price_data.get("bb_upper"),
                "bb_lower": price_data.get("bb_lower"),
                "stochastic": price_data.get("stochastic"),
            }
        ),
        200,
    )


# Abonelik planını güncelleme endpoint'i
@api_bp.route("/update_subscription", methods=["POST"])
@limiter.limit(get_plan_rate_limit, key_func=rate_limit_key_func)
@require_subscription_plan(
    SubscriptionPlan.TRIAL
)  # Abone olunan endpoint'e erişim için minimum TRIAL planı
def update_subscription():
    user = g.user  # Dekorator'den gelen kullanıcı objesi
    data = request.get_json()
    plan_str = data.get("plan")
    promo_code_str = data.get("promo_code")
    # payment_id artık bu endpoint'te kullanılmıyor.

    # EK: KULLANICI BAŞINA PLAN DEĞİŞİKLİĞİ RATE-LIMIT KONTROLÜ (REDIS)
    redis_client = current_app.extensions.get("redis_client")
    if redis_client:  # Redis aktifse
        limit_key = f"user:plan_update:{user.id}"
        now = int(time.time())
        pipe = redis_client.pipeline()
        pipe.lpush(limit_key, now)  # Her denemede zaman damgasını ekle
        pipe.ltrim(
            limit_key, 0, PLAN_UPDATE_LIMIT_PER_MINUTE - 1
        )  # Sadece son 'limit' kadar elemanı tut
        pipe.expire(
            limit_key, PLAN_UPDATE_WINDOW_SECONDS
        )  # Anahtarın yaşam süresini ayarla
        pipe.execute()

        # Redis'ten okunan recent_attempts listesi byte string olarak döner, int'e çevirilmeli
        recent_attempts_bytes = redis_client.lrange(limit_key, 0, -1)
        recent_attempts = [int(ts) for ts in recent_attempts_bytes]

        # Kontrol: Eğer pencere içinde limitten fazla deneme varsa (ltrim'den sonra liste boyutu limit+1 olur)
        if len(recent_attempts) > PLAN_UPDATE_LIMIT_PER_MINUTE:
            logger.warning(
                f"Kullanıcı {user.username} çok sık plan değişikliği deniyor (Redis limit)."
            )
            add_audit_log(
                action_type="PLAN_UPDATE_RATE_LIMIT_BLOCKED",
                actor_id=user.id,
                actor_username=user.username,
                target_id=user.id,
                target_username=user.username,
                details={
                    "window_seconds": PLAN_UPDATE_WINDOW_SECONDS,
                    "limit": PLAN_UPDATE_LIMIT_PER_MINUTE,
                    "recent_attempts_timestamps": recent_attempts,
                    "ip_address": request.remote_addr,
                },
                ip_address=request.remote_addr,
                commit=True,
            )
            # Düzeltilen değişken adı: PLAN_UPDATE_LIMIT_PER_MINUTE
            return (
                jsonify(
                    {
                        "error": f"Plan değişikliği limiti: {PLAN_UPDATE_WINDOW_SECONDS} saniyede {PLAN_UPDATE_LIMIT_PER_MINUTE} kez. Lütfen bekleyin."
                    }
                ),
                429,
            )

    if not plan_str:
        return jsonify({"error": "Plan bilgisi eksik."}), 400

    with current_app.app_context():
        try:
            selected_plan = SubscriptionPlan[plan_str.upper()]
        except KeyError:
            return jsonify({"error": "Geçersiz abonelik planı."}), 400

        old_level = user.subscription_level.name

        # Kullanıcının mevcut planı, yükseltmeye çalıştığı plandan daha iyi veya aynı seviyede ise hata döndür
        if user.subscription_level.value >= selected_plan.value:
            return (
                jsonify(
                    {
                        "error": f"Mevcut planınız ({user.subscription_level.name}) seçilen plandan daha iyi veya aynı seviyede."
                    }
                ),
                400,
            )

        try:  # Tüm abonelik güncelleme işlemini bir transaction'a al
            # --- Plan Yükseltme/Değişim Mantığı ---
            # Bu endpoint sadece promosyon kodları ile yükseltme veya TRIAL -> BASIC geçişi gibi özel durumları işler.
            # ÖDEME İLE YÜKSELTME ARTIK iyzico CALLBACK ENDPOINT'İNDE (backend/payment/routes.py) YÖNETİLİR.

            if promo_code_str:
                promo_code = (
                    PromoCode.query.filter_by(code=promo_code_str, is_active=True)
                    .with_for_update()
                    .first()
                )
                if not promo_code:
                    add_audit_log(
                        action_type="PROMO_CODE_APPLY_FAILED_INVALID",
                        actor_id=user.id,
                        actor_username=user.username,
                        target_id=None,
                        target_username=promo_code_str,
                        details={
                            "reason": "Invalid or inactive promo code",
                            "ip_address": request.remote_addr,
                        },
                        ip_address=request.remote_addr,
                        commit=False,  # Audit log aynı transaction'da
                    )
                    db.session.commit()  # Audit logu commit et (fail-fast)
                    return (
                        jsonify(
                            {"error": "Geçersiz veya aktif olmayan promosyon kodu."}
                        ),
                        400,
                    )

                if promo_code.expires_at and datetime.utcnow() > promo_code.expires_at:
                    promo_code.is_active = False  # Deaktive et
                    add_audit_log(
                        action_type="PROMO_CODE_APPLY_FAILED_EXPIRED",
                        actor_id=user.id,
                        actor_username=user.username,
                        target_id=promo_code.id,
                        target_username=promo_code.code,
                        details={
                            "reason": "Promo code expired",
                            "ip_address": request.remote_addr,
                        },
                        ip_address=request.remote_addr,
                        commit=False,
                    )
                    db.session.commit()  # Audit logu commit et (fail-fast)
                    return jsonify({"error": "Promosyon kodunun süresi dolmuş."}), 400

                if promo_code.current_uses >= promo_code.max_uses:
                    promo_code.is_active = False  # Deaktive et
                    add_audit_log(
                        action_type="PROMO_CODE_APPLY_FAILED_MAX_USES",
                        actor_id=user.id,
                        actor_username=user.username,
                        target_id=promo_code.id,
                        target_username=promo_code.code,
                        details={
                            "reason": "Max uses exceeded",
                            "ip_address": request.remote_addr,
                        },
                        ip_address=request.remote_addr,
                        commit=False,
                    )
                    db.session.commit()  # Audit logu commit et (fail-fast)
                    return (
                        jsonify({"error": "Promosyon kodunun kullanım limiti dolmuş."}),
                        429,
                    )

                if promo_code.is_single_use_per_user:
                    existing_usage = PromoCodeUsage.query.filter_by(
                        user_id=user.id, promo_code_id=promo_code.id
                    ).first()
                    if existing_usage:
                        add_audit_log(
                            action_type="PROMO_CODE_APPLY_FAILED_ALREADY_USED",
                            actor_id=user.id,
                            actor_username=user.username,
                            target_id=promo_code.id,
                            target_username=promo_code.code,
                            details={
                                "reason": "Already used by user",
                                "ip_address": request.remote_addr,
                            },
                            ip_address=request.remote_addr,
                            commit=False,
                        )
                        db.session.commit()
                        return (
                            jsonify(
                                {"error": "Bu promosyon kodunu daha önce kullandınız."}
                            ),
                            429,
                        )

                user.subscription_level = promo_code.plan
                if user.subscription_end and user.subscription_end > datetime.utcnow():
                    user.subscription_end += timedelta(days=promo_code.duration_days)
                else:
                    user.subscription_end = datetime.utcnow() + timedelta(
                        days=promo_code.duration_days
                    )

                max_allowed_end_date = datetime.utcnow() + timedelta(
                    days=MAX_SUBSCRIPTION_EXTENSION_DAYS
                )
                if user.subscription_end > max_allowed_end_date:
                    user.subscription_end = max_allowed_end_date
                    logger.warning(
                        f"Kullanıcı {user.username} - Promosyon ile maksimum abonelik süresine ulaşıldı."
                    )
                    add_audit_log(
                        action_type="SUBSCRIPTION_EXTENDED_TO_MAX_LIMIT",
                        actor_id=user.id,
                        actor_username=user.username,
                        target_id=user.id,
                        target_username=user.username,
                        details={
                            "promo_code": promo_code.code,
                            "reason": "Max subscription duration reached",
                            "new_end_date": user.subscription_end.isoformat(),
                        },
                        ip_address=request.remote_addr,
                        commit=False,
                    )

                promo_code.current_uses += 1
                if promo_code.current_uses >= promo_code.max_uses:
                    promo_code.is_active = False

                new_usage = PromoCodeUsage(promo_code_id=promo_code.id, user_id=user.id)
                db.session.add(new_usage)

                logger.info(
                    f"Kullanıcı {user.username} için promosyon kodu '{promo_code_str}' uygulandı. Yeni plan: {user.subscription_level.name}."
                )
                add_audit_log(
                    action_type="PROMO_CODE_APPLIED",
                    actor_id=user.id,
                    actor_username=user.username,
                    target_id=promo_code.id,
                    target_username=promo_code.code,
                    details={
                        "old_plan": old_level,
                        "new_plan": user.subscription_level.name,
                        "ip_address": request.remote_addr,
                    },
                    ip_address=request.remote_addr,
                    commit=False,
                )

            # Promosyon kodu yoksa ve ödeme bilgisi yoksa, reddet.
            # payment_id artık bu endpoint'te işlenmiyor.
            else:
                add_audit_log(
                    action_type="SUBSCRIPTION_UPGRADE_FAILED_NO_PROMO",
                    actor_id=user.id,
                    actor_username=user.username,
                    target_id=user.id,
                    target_username=user.username,
                    details={
                        "old_plan": old_level,
                        "new_plan_attempted": selected_plan.name,
                        "ip_address": request.remote_addr,
                        "reason": "No promo code provided",
                    },
                    ip_address=request.remote_addr,
                    commit=True,  # Hata olduğu için commit et
                )
                return (
                    jsonify(
                        {"error": "Yükseltme için geçerli bir promosyon kodu gerekli."}
                    ),
                    400,
                )

            user.token_version += 1
            db.session.commit()
            logger.info(
                f"Kullanıcı {user.username} abonelik seviyesi {old_level} -> {user.subscription_level.name} olarak güncellendi."
            )

            return (
                jsonify(
                    {
                        "status": f"{user.subscription_level.name.capitalize()} planına geçiş yapıldı.",
                        "subscription_level": user.subscription_level.name,
                    }
                ),
                200,
            )

        except IntegrityError as ie:
            db.session.rollback()
            logger.error(
                f"Abonelik güncellenirken IntegrityError: {ie}. Kullanıcı: {user.username}"
            )
            add_audit_log(
                action_type="SUBSCRIPTION_UPDATE_FAILED_DB_INTEGRITY",
                actor_id=user.id,
                actor_username=user.username,
                target_id=user.id,
                target_username=user.username,
                details={"error": str(ie), "ip_address": request.remote_addr},
                ip_address=request.remote_addr,
                commit=True,
            )
            return (
                jsonify(
                    {
                        "error": "Abonelik güncellenirken bir veritabanı hatası oluştu. Lütfen tekrar deneyin veya destek ile iletişime geçin."
                    }
                ),
                500,
            )
        except Exception as e:
            db.session.rollback()
            logger.exception(
                f"Abonelik güncellenirken beklenmeyen hata: {e}. Kullanıcı: {user.username}"
            )
            add_audit_log(
                action_type="SUBSCRIPTION_UPDATE_FAILED_UNEXPECTED",
                actor_id=user.id,
                actor_username=user.username,
                target_id=user.id,
                target_username=user.username,
                details={"error": str(e), "ip_address": request.remote_addr},
                ip_address=request.remote_addr,
                commit=True,
            )
            return (
                jsonify(
                    {
                        "error": "Abonelik güncellenirken bir sorun oluştu. Destek ile iletişime geçin."
                    }
                ),
                500,
            )


# Kullanıcının mevcut abonelik durumunu getirme endpoint'i
@api_bp.route("/get_subscription_status", methods=["GET"])
@limiter.limit(get_plan_rate_limit, key_func=rate_limit_key_func)
@require_subscription_plan(
    SubscriptionPlan.TRIAL
)  # En az TRIAL planı gereklidir (herkes görebilir)
def get_subscription_status():
    user = g.user  # Dekorator'den gelen kullanıcı objesi

    # Kullanıcı verilerini güvenli serializer ile döndür
    user_data = serialize_user_for_api(user, scope="self")

    return (
        jsonify(
            {
                "subscription_level": user_data["subscription_level"],
                "is_active": user_data["is_active"],
                "subscription_end": user_data["subscription_end"],
                "subscription_start": user_data["subscription_start"],
                "username": user_data["username"],
                "email": user_data["email"],
                "api_key": user_data["api_key"],
                "is_locked": user_data["is_locked"],
                "locked_until": user_data["locked_until"],
            }
        ),
        200,
    )


# Kullanıcı profil ve limit bilgisini döndüren yeni endpoint
@api_bp.route("/user/me", methods=["GET"])
@limiter.limit(get_plan_rate_limit, key_func=rate_limit_key_func)
@require_subscription_plan(SubscriptionPlan.TRIAL)
def get_user_profile():
    user = g.user
    # Tek kaynak: decorator ile aynı sayaç/veri modeli
    status = get_usage_status(str(user.id), "coin_analysis")
    used = status.get("used", 0)
    max_daily = status.get("quota", 0)
    remaining = status.get("remaining", None)
    user_data = serialize_user_for_api(user, scope="self")
    return (
        jsonify(
            {
                "user": user_data,
                "limits": {
                    "used_prediction_today": used,
                    "remaining_prediction_today": remaining,
                    "daily_quota": max_daily,
                },
                "plan": user.plan.to_dict() if user.plan else None,
            }
        ),
        200,
    )


# Kullanıcının kendi aboneliğini yükseltmesi için PATCH endpoint'i
@api_bp.route("/users/<int:user_id>/upgrade_plan", methods=["PATCH"])
@limiter.limit(get_plan_rate_limit, key_func=rate_limit_key_func)
@require_subscription_plan(SubscriptionPlan.TRIAL)
def upgrade_plan(user_id):
    user = g.user
    if user.id != user_id:
        return (
            jsonify({"error": "Sadece kendi aboneliğinizi güncelleyebilirsiniz."}),
            403,
        )
    data = request.get_json() or {}
    plan_str = data.get("plan")
    if not plan_str:
        return jsonify({"error": "Plan bilgisi eksik."}), 400
    try:
        new_plan = SubscriptionPlan[plan_str.upper()]
    except KeyError:
        return jsonify({"error": "Geçersiz abonelik planı."}), 400
    if user.subscription_level.value >= new_plan.value:
        return (
            jsonify(
                {"error": "Mevcut planınız seçilen plandan daha yüksek veya eşit."}
            ),
            400,
        )
    user.subscription_level = new_plan
    user.subscription_start = datetime.utcnow()
    user.subscription_end = datetime.utcnow() + timedelta(
        days=SUBSCRIPTION_EXTENSION_DAYS
    )
    db.session.commit()
    add_audit_log(
        action_type="PLAN_UPGRADED",
        actor_id=user.id,
        actor_username=user.username,
        target_id=user.id,
        target_username=user.username,
        details={"new_plan": new_plan.name},
        ip_address=request.remote_addr,
        commit=True,
    )
    return jsonify({"subscription_level": new_plan.name, "status": "upgraded"}), 200


# ---------------------------------------------------------------------------
# User Activity Endpoint
# ---------------------------------------------------------------------------


@api_bp.route("/user/activity", methods=["GET"])
@jwt_required()
@limiter.limit("30 per hour")
def get_user_activity():
    """Return recent security events for the current user."""
    try:
        uid = get_jwt_identity()
        events = (
            SecurityEvent.query.filter_by(user_id=uid)
            .order_by(SecurityEvent.timestamp.desc())
            .limit(50)
            .all()
        )
        activity_data = []
        for event in events:
            activity_data.append(
                {
                    "event_type": event.event_type,
                    "timestamp": event.timestamp.isoformat(),
                    "success": event.success,
                    "ip_address": event.ip_address[-4:] if event.ip_address else None,
                    "details": (
                        (event.details or {})
                        .get("user_agent_analysis", {})
                        .get("browser")
                        if event.details
                        else None
                    ),
                }
            )
        return jsonify({"activity": activity_data})
    except Exception:
        return jsonify({"error": "Failed to retrieve activity"}), 500


# Blueprint'e özel hata yakalama (limiter'ın hata fırlatması durumunda)
@api_bp.errorhandler(429)
def ratelimit_handler(e):
    logger.warning(
        f"API Blueprint Rate limit aşıldı: {request.remote_addr} - {e.description}"
    )
    # Audit log
    add_audit_log(
        action_type="RATE_LIMIT_EXCEEDED",
        actor_id=None,  # API Key'den user bulunabilir, ama burada generic
        actor_username=request.headers.get("X-API-KEY", request.remote_addr),
        target_username="N/A",
        details={
            "path": request.path,
            "ip_address": request.remote_addr,
            "limit_info": str(e.description),
        },
        ip_address=request.remote_addr,
        commit=True,  # add_audit_log kendi commitini yapar
    )
    return (
        jsonify(
            {
                "error": "Çok fazla istek gönderildi. Lütfen daha sonra tekrar deneyin.",
                "limit_info": str(e.description),
            }
        ),
        429,
    )


@api_bp.route("/analyze", methods=["POST"])
@jwt_required()
@require_subscription_plan(SubscriptionPlan.BASIC)
@validate_json(CryptoAnalysisRequestSchema)
def analyze_crypto(validated_data):
    """Analyze cryptocurrency with validated input and sanitized output."""
    try:
        symbol = validated_data.symbol
        timeframe = validated_data.timeframe
        indicators = validated_data.indicators
        start_date = validated_data.start_date
        end_date = validated_data.end_date

        current_user_id = get_jwt_identity()
        user = SecureQueryManager.get_user_by_id(current_user_id)
        if not user:
            return jsonify({"error": "Invalid user"}), 401

        result = {
            "symbol": symbol,
            "timeframe": timeframe,
            "indicators": indicators,
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None,
        }
        sanitized_result = sanitize_analysis_result(result)
        return jsonify(sanitized_result)
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Analysis error for user %s: %s", current_user_id, exc)
        return (
            jsonify({"error": "Analysis failed", "message": "Internal server error"}),
            500,
        )


def sanitize_analysis_result(result):
    """Recursively sanitize analysis results to prevent XSS."""
    if isinstance(result, dict):
        return {k: sanitize_analysis_result(v) for k, v in result.items()}
    if isinstance(result, list):
        return [sanitize_analysis_result(item) for item in result]
    if isinstance(result, str):
        return html.escape(result)
    return result


@api_bp.route("/admin/analytics", methods=["POST"])
@jwt_required()
@admin_required()
@validate_json(AdminAnalyticsRequestSchema)
def admin_analytics(validated_data):
    """Return user analytics data for admins."""
    try:
        start_date = validated_data.start_date
        end_date = validated_data.end_date
        metric_type = validated_data.metric_type

        analytics_data = SecureQueryManager.get_user_analytics_secure(
            start_date=start_date.isoformat(), end_date=end_date.isoformat()
        )
        if "error" in analytics_data:
            return jsonify({"error": "Failed to fetch analytics"}), 500
        return jsonify({"data": analytics_data, "metric_type": metric_type})
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Admin analytics error: %s", exc)
        return jsonify({"error": "Analytics request failed"}), 500
