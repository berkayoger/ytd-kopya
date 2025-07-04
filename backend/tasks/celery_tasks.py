"""Celery task definitions."""

from datetime import datetime
import json
import traceback
from dataclasses import asdict
import numpy as np

from backend import celery_app, socketio, logger, create_app
from backend.core.services import YTDCryptoSystem, AnalysisResult
from backend.db.models import (
    User,
    SubscriptionPlan,
    CeleryTaskLog,
    CeleryTaskStatus,
)
from backend import db

app = create_app()


@celery_app.task(name="backend.tasks.celery_tasks.run_full_analysis", bind=True)
def run_full_analysis(self, coin_id: str, investor_profile: str = "moderate", user_id: int | None = None):
    logger.info(
        f"Celery: {coin_id.upper()} analizi arka planda baslatildi. Profil: {investor_profile}"
    )
    with app.app_context():
        system = YTDCryptoSystem()
        user = User.query.get(user_id) if user_id is not None else None

        log = CeleryTaskLog(
            task_id=self.request.id,
            task_name=self.name,
            status=CeleryTaskStatus.STARTED,
        )
        db.session.add(log)
        db.session.commit()

        try:
            price_data = system.collector.collect_price_data(coin_id)
            onchain = system.collector.collect_onchain_data(coin_id)
            social = system.collector.collect_social_data(coin_id)
            news = system.collector.collect_news_data(coin_id)
            all_news_text = " ".join(
                f"{n.get('title','')} {n.get('description','')}" for n in news
            )

            _, news_score = system.ai.analyze_sentiment(all_news_text)
            (
                forecast,
                _method,
                forecast_bounds,
                _dates,
                _confidence,
                forecast_exp,
            ) = system.ai.forecast(
                price_data["prices"],
                price_data["times"],
                coin_name=coin_id,
            )

            volatility = float(np.std(price_data["prices"]) / np.mean(price_data["prices"]))

            decision_input = {
                "current_price": price_data["current_price"],
                "rsi": price_data["rsi"],
                "macd": price_data["macd"],
                "bb_upper": price_data["bb_upper"],
                "bb_lower": price_data["bb_lower"],
                "stochastic": price_data["stochastic"],
                "news_sentiment": news_score,
                **social,
                **onchain,
                "volatility": volatility,
            }

            decision = system.engine.decide(decision_input, investor_profile)

            analysis_result = AnalysisResult(
                coin=coin_id,
                timestamp=datetime.utcnow(),
                rsi=price_data["rsi"],
                macd=price_data["macd"],
                bb_upper=price_data["bb_upper"],
                bb_lower=price_data["bb_lower"],
                stochastic=price_data["stochastic"],
                candlestick_pattern=price_data["candlestick_pattern"],
                news_sentiment=news_score,
                twitter_sentiment=social["twitter_sentiment"],
                social_volume=social["social_volume"],
                active_addresses=onchain["active_addresses"],
                exchange_inflow=onchain["exchange_inflow"],
                exchange_outflow=onchain["exchange_outflow"],
                forecast_next_day=forecast,
                forecast_explanation=forecast_exp,
                forecast_upper_bound=forecast_bounds.get("upper"),
                forecast_lower_bound=forecast_bounds.get("lower"),
                volatility=volatility,
                signal=decision["signal"],
                confidence=decision["confidence"],
                risk_level="high" if volatility > 0.1 else "medium" if volatility > 0.05 else "low",
                suggested_stop_loss=decision["stop_loss"],
                suggested_position_size=decision["position_size_pct"],
            )

            system.save_to_dbh(analysis_result)

            result_dict = asdict(analysis_result)
            log.status = CeleryTaskStatus.SUCCESS
            log.result = json.dumps(result_dict)
            log.completed_at = datetime.utcnow()
            db.session.commit()

            if socketio:
                socketio.emit(
                    "analysis_completed",
                    {"coin": coin_id, "result": result_dict},
                    namespace="/",
                )

            return result_dict
        except Exception as e:  # pragma: no cover - logging
            log.status = CeleryTaskStatus.FAILURE
            log.traceback = traceback.format_exc()
            log.completed_at = datetime.utcnow()
            db.session.commit()
            logger.error(f"Celery gorevi sirasinda hata: {e}")
            raise


@celery_app.task(name="backend.tasks.celery_tasks.analyze_coin_task")
def analyze_coin_task(coin_id: str, investor_profile: str = "moderate", user_id: int | None = None):
    """Backward compatible wrapper for the analysis task."""
    return run_full_analysis(coin_id, investor_profile, user_id)


@celery_app.task
def check_and_downgrade_subscriptions():
    """Downgrade expired or trial subscriptions to BASIC."""
    logger.info("Celery: abonelikleri kontrol ediyor.")
    with app.app_context():
        now = datetime.utcnow()
        users = User.query.all()
        for user in users:
            if user.subscription_end and user.subscription_end < now:
                user.subscription_level = SubscriptionPlan.BASIC
                user.subscription_end = None
                logger.info(f"Kullanici {user.username} aboneligi sona erdi, BASIC plana dusuruldu.")
        db.session.commit()


from backend.utils.alarms import send_alarm, AlarmSeverityEnum

@celery_app.task
def send_security_alert_task(alert_type: str, details: str = "", severity: str = "INFO"):
    """Send a security alert to external channels."""
    logger.warning(f"Security alert: {alert_type} - {details}")
    with app.app_context():
        sev = AlarmSeverityEnum[severity] if isinstance(severity, str) else severity
        send_alarm(alert_type, sev, details)
