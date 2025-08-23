# Pytest için global ayarlar: offline ve determinizm
import os
import pytest
from typing import Iterator

# CoinGecko şimini çevrimdışı modda çalıştır, bekleme yok
os.environ.setdefault("COINGECKO_SHIM_OFFLINE", "1")
os.environ.setdefault("COINGECKO_MIN_INTERVAL_SEC", "0")

# Uygulama testleri için standart ortam değişkenleri
os.environ.setdefault("FLASK_ENV", "testing")
os.environ.setdefault("PYTHONHASHSEED", "0")


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    """Testlerde dış ağ bağlantılarını engelle."""
    import socket

    def guard(*args, **kwargs):
        raise RuntimeError("Test sırasında ağ erişimi engellendi")

    # Gerçek ağ gerekliyse bu iki satırı yorum satırına al.
    monkeypatch.setattr(socket, "create_connection", guard, raising=True)
    monkeypatch.setattr(
        socket,
        "socket",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("Test sırasında ağ engellendi")),
    )
    yield



# ---- Flask test client fallback ---------------------------------------------
# Bazı ortamlarda pytest-flask kurulu olmayabilir. tests/ tarafında zaten bir
# `app` fixture'ı görünür durumda; yalnızca `client` eksik. Burada hafif bir
# client fixture'ı sağlayarak bağımlılık olmadan çalıştırıyoruz.
@pytest.fixture
def client(app) -> Iterator:
    """Flask test client (pytest-flask olmadan sade fallback)."""
    with app.test_client() as c:
        # İsteyen testler context'e ihtiyaç duyarsa app fixture'ı zaten sağlıyor.
        yield c
