from flask import Blueprint, request, jsonify, g, current_app

import pandas as pd
from typing import Any, Dict, List
from dataclasses import asdict

from backend.decision_engine import extract_features, make_decision
from backend.decision_engine.score_calculator import calculate_score
from backend.engine.strategic_decision_engine import advanced_decision_logic
from backend.auth.jwt_utils import jwt_required_if_not_testing
from backend.middleware.plan_limits import enforce_plan_limit
from backend.utils.feature_flags import feature_flag_enabled
from backend.utils.logger import create_log
from backend.decision_engines import (
    ENGINE_REGISTRY,
    DecisionRequest,
    OrchestratorConfig,
    build_consensus_result,
)

# Blueprint for lightweight decision endpoints
decision_bp = Blueprint('decision', __name__, url_prefix='/api/decision')


@decision_bp.route('/evaluate', methods=['POST'])
def evaluate_decision():
    """Return decision signal and weighted score for provided indicators."""
    data = request.get_json() or {}

    # Extract normalized features and calculate weighted score
    features = extract_features(data)
    score = calculate_score(features)

    # Map data to inputs expected by advanced_decision_logic
    indicators = {
        'rsi': data.get('rsi'),
        'macd': data.get('macd'),
        'macd_signal': data.get('macd_signal'),
        'price': data.get('price'),
        'sma_10': data.get('sma_10'),
        'prev_predictions_success_rate': data.get('prev_predictions_success_rate', 0),
    }
    decision = advanced_decision_logic(indicators)

    return jsonify({'decision': decision, 'score': score, 'features': features})


@decision_bp.route('/predict', methods=['POST'])
def predict_decision():
    """Return a recommendation based on provided market indicators."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON"}), 400

    features = extract_features(data)
    score = calculate_score(features)
    coin = data.get("coin", "UNKNOWN")
    result = make_decision(coin, score)
    return jsonify(result)


@decision_bp.route('/score-multi', methods=['POST'])
@jwt_required_if_not_testing()
@enforce_plan_limit("predict_daily")
def score_multi():
    """Çoklu motor çıktısından konsensüs kararı üretir."""

    if not feature_flag_enabled("decision_consensus"):
        return jsonify({"error": "Özellik şu anda devre dışı."}), 403

    user = g.get("user")
    ip_addr = request.remote_addr or "unknown"
    ua = request.headers.get("User-Agent", "")
    status = "success"
    try:
        # -------- Minimal şema doğrulama / normalize --------
        def _bad(msg: str, code: int = 400):
            return jsonify({"error": msg}), code

        payload = request.get_json() or {}
        symbol = (payload.get("symbol") or "").strip()
        timeframe = (payload.get("timeframe") or "").strip()
        engines: List[str] = payload.get("engines") or []
        params = payload.get("params", {}) or {}
        account_value = payload.get("account_value")

        if not symbol or not timeframe:
            return _bad("symbol ve timeframe zorunludur")

        df = pd.DataFrame(payload.get("ohlcv", []))
        required = {"ts", "open", "high", "low", "close", "volume"}
        if not required.issubset(df.columns):
            return _bad(f"ohlcv zorunlu kolonlar: {sorted(required)}")
        df = df.copy()
        df["ts"] = pd.to_datetime(df["ts"], errors="coerce", utc=True)
        for c in ["open", "high", "low", "close", "volume"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        df = df.dropna(subset=["ts", "open", "high", "low", "close"]).sort_values("ts")
        if len(df) < 50:
            return _bad("en az 50 bar gerekli")

        # Motor listesi boşsa registry’den doldur
        if not engines:
            engines = list(ENGINE_REGISTRY.keys())
        unknown = [e for e in engines if e not in ENGINE_REGISTRY]
        if unknown:
            return _bad(f"Bilinmeyen motor(lar): {unknown}")

        results: Dict[str, Any] = {}
        for eid in engines:
            eng_cls = ENGINE_REGISTRY[eid]
            eng = eng_cls()
            req = DecisionRequest(
                engine_id=eid,
                symbol=symbol,
                timeframe=timeframe,
                ohlcv=df,
                params=params.get(eid, {}),
            )
            results[eid] = eng.run(req)

        if not results:
            return jsonify({"error": "çalıştırılacak motor bulunamadı"}), 400

        consensus = build_consensus_result(
            symbol, timeframe, df, results, OrchestratorConfig(), account_value
        )
        # Dataclass sonuçlarını güvenli serileştir
        consensus["engines"] = {k: asdict(v) for k, v in results.items()}
        return jsonify(consensus)
    except Exception as exc:  # pragma: no cover
        status = "error"
        current_app.logger.exception("score_multi hata: %s", exc)
        return jsonify({"error": "internal"}), 500
    finally:
        if user:
            # Bazı test fixture'larında 'username' olmayabiliyor (SimpleNamespace)
            uid = getattr(user, "id", None)
            uname = (
                getattr(user, "username", None)
                or getattr(user, "email", None)
                or (str(uid) if uid is not None else "anonymous")
            )
            create_log(
                user_id=str(uid) if uid is not None else "anonymous",
                username=str(uname),
                ip_address=ip_addr,
                action="decision_consensus",
                target="/api/decision/score-multi",
                description="Konsensüs kararı",
                status=status,
                user_agent=ua,
            )
