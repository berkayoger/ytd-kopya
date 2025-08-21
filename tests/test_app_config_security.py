import importlib
import sys


def _reload_config_module():
    sys.modules.pop("app.config", None)
    import app.config as config_module  # type: ignore
    return importlib.reload(config_module)


def test_validate_config_reports_missing_keys(monkeypatch):
    monkeypatch.delenv("COINGECKO_API_KEY", raising=False)
    monkeypatch.delenv("CRYPTOCOMPARE_API_KEY", raising=False)
    monkeypatch.setenv("JWT_SECRET_KEY", "a" * 64)
    config_module = _reload_config_module()
    result = config_module.Config.validate_config()
    assert "COINGECKO_API_KEY ayarlanmadı" in result["issues"]


def test_mask_sensitive_values():
    from app.config import Config

    data = {"SECRET_KEY": "abcd1234", "NORMAL": "deger"}
    masked = Config.mask_sensitive_values(data)
    assert masked["SECRET_KEY"] == "****1234"
    assert masked["NORMAL"] == "deger"

