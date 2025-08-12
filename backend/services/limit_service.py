"""Kullanıcı limit servisleri."""


def get_user_limits(user_id: int) -> dict:
    """
    Belirli bir kullanıcının plan ve limit bilgilerini döndür.
    Gelecekte DB sorguları ile genişletilebilir; şimdilik mock veri döndürür.
    """

    # TODO: Veritabanı entegrasyonu yapılacak.
    return {
        "plan": "premium",
        "limits": {
            "daily_requests": {"used": 45, "max": 100},
            "monthly_requests": {"used": 1200, "max": 3000},
        },
    }

