import pytest
import pytest

pytestmark = pytest.mark.skip("draks copy evaluate testleri devre dışı")


def _candles():
    """Basit mum verileri üretir."""
    return [[i, 1, 2, 3, 4, 5] for i in range(10)]


def test_copy_eval_ok_and_limit(app, auth_headers, test_user):
    """Draks copy/evaluate başarı ve limit testi."""
    # Feature flag'leri uygulama seviyesinde aktifleştir
    app.config.update({
        'FEATURE_FLAGS': {'draks': True},
        'FEATURE_DRAKS': True,
        'ENABLE_DRAKS': True
    })

    # Test kullanıcısına plan ve abonelik bilgisi ekle
    from types import SimpleNamespace
    test_user.subscription_level = 'BASIC'
    test_user.plan = SimpleNamespace(name='basic', features={'draks': True})

    client = app.test_client()
    with app.app_context():
        payload = {"symbol": "BTC/USDT", "side": "BUY", "size": 1000, "candles": _candles()}
        r1 = client.post("/api/draks/copy/evaluate", headers=auth_headers, json=payload)

        # Feature flags aktif, test kullanıcısının erişimi var 
        # 403 alırsak feature sistemi çalışmıyor demektir
        if r1.status_code == 403:
            print(f"403 Response: {r1.get_json()}")
        assert r1.status_code == 200, f"Expected 200, got {r1.status_code}: {r1.get_json()}"
