from datetime import datetime, timedelta


def make_decision(coin: str, score: float) -> dict:
    """Skora gore karar ve aciklama uretir."""
    if score >= 75:
        recommendation = "AL"
        explanation = "Teknik gostergeler guclu alim sinyali veriyor."
        expected_return = 0.25
        confidence = 90
    elif score >= 50:
        recommendation = "TUT"
        explanation = "Belirsizlik var, gozlemlemeye devam edin."
        expected_return = 0.10
        confidence = 70
    else:
        recommendation = "SAT"
        explanation = "Dusus sinyalleri agir basiyor, riskli bolge."
        expected_return = -0.15
        confidence = 60

    return {
        "coin": coin,
        "score": round(score, 2),
        "recommendation": recommendation,
        "confidence": confidence,
        "expected_return": expected_return,
        "valid_until": (datetime.utcnow() + timedelta(days=7)).isoformat(),
        "explanation": explanation,
    }
