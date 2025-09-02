# Sadece get_usage_count fonksiyonu için düzeltme
def get_usage_count(user_or_id, feature_key: str) -> int:
    """
    Günlük kullanım sayısı - basitleştirilmiş versiyon
    Args:
        user_or_id: User objesi veya user_id (string/int)
        feature_key: Özellik adı (örn: "predict_daily")
    """
    try:
        from backend.db.models import UsageLog
    except Exception:
        return 0

    # User ID'yi çıkar
    if hasattr(user_or_id, "id"):
        uid = user_or_id.id
    else:
        uid = user_or_id

    try:
        # Bugünün başından itibaren say
        start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        count = (
            UsageLog.query.filter_by(user_id=uid, action=feature_key)
            .filter(UsageLog.timestamp >= start)
            .count()
        )
        return count
    except Exception:
        return 0
