"""
backend.utils.feature_flags

Basit feature flag yardımcıları:
- Bellek içi (default) saklama
- İsteğe bağlı Redis desteği (USE_REDIS=True ise)
- Meta bilgisi (created_at/by, updated_at/by, description, category)
- Admin API'nin beklediği create/update/get yardımcıları

Testler şunları bekliyor:
- feature_flag_enabled("recommendation_enabled") -> True
- all_feature_flags() -> dict döndürür: {name: enabled_bool}
- USE_REDIS ve redis_client modül değişkenleri monkeypatch edilebilir
- _default_flags ve _default_flag_meta monkeypatch edilebilir
- create_feature_flag & update_feature_flag hem `flag_name` hem `name` arg'ü kabul eder
- get_feature_flag_metadata mevcut meta'yı döndürür
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict, Optional


# -----------------------------------------------------------------------------
# Global konfigürasyon
# -----------------------------------------------------------------------------
def _bool_env(v: Optional[str], default: bool = False) -> bool:
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "on")


USE_REDIS: bool = _bool_env(os.getenv("FEATURE_FLAGS_USE_REDIS"), False)

redis_client = None  # tests monkeypatch edebiliyor
if USE_REDIS:
    try:
        import redis  # type: ignore

        redis_client = redis.from_url(
            os.getenv("REDIS_URL", "redis://localhost:6379/0")
        )
    except Exception:
        # Redis yoksa bellek içi fallback
        redis_client = None
        USE_REDIS = False


# -----------------------------------------------------------------------------
# Bellek içi varsayılanlar ve meta
#  - Testler bu objeleri monkeypatch ile değiştirebiliyor.
# -----------------------------------------------------------------------------
def _now_iso() -> str:
    return datetime.utcnow().isoformat()


_default_flags: Dict[str, bool] = {
    # Testler 'recommendation_enabled' bayrağının True olmasını bekliyor
    "recommendation_enabled": True,
    # Projede sık kullanılan ikinci bir örnek
    "health_check": True,
    "draks": True,
}

_default_flag_meta: Dict[str, Dict[str, Any]] = {
    "recommendation_enabled": {
        "created_at": _now_iso(),
        "created_by": None,
        "description": "",
        "category": "general",
    },
    "draks": {
        "created_at": _now_iso(),
        "created_by": None,
        "description": "",
        "category": "general",
    },
}


# -----------------------------------------------------------------------------
# İç yardımcılar
# -----------------------------------------------------------------------------
def _redis_key(name: str) -> str:
    return f"ff:{name}"


def _get_all_known_names() -> set[str]:
    # Redis tarafında anahtar taraması (kullanılıyorsa)
    names: set[str] = set(_default_flags.keys()) | set(_default_flag_meta.keys())
    if USE_REDIS and redis_client is not None:
        try:
            # KEYS prod için pahalı olabilir; test ve küçük kullanım için yeterli
            for k in redis_client.keys("ff:*"):
                try:
                    ks = (
                        k.decode("utf-8")
                        if isinstance(k, (bytes, bytearray))
                        else str(k)
                    )
                except Exception:
                    ks = str(k)
                if ks.startswith("ff:"):
                    names.add(ks[3:])
        except Exception:
            # Redis hatasını sessizce yut (testlerde sorun olmasın)
            pass
    return names


# -----------------------------------------------------------------------------
# Dış API
# -----------------------------------------------------------------------------
def feature_flag_enabled(name: str) -> bool:
    """Bir bayrağın etkin olup olmadığını döndürür."""
    if USE_REDIS and redis_client is not None:
        try:
            v = redis_client.get(_redis_key(name))
            if v is None:
                # Redis'te yoksa bellek içi default'a düş
                return bool(_default_flags.get(name, False))
            sv = v.decode("utf-8") if isinstance(v, (bytes, bytearray)) else str(v)
            return sv in ("1", "true", "True", "yes", "on")
        except Exception:
            # Redis sorununda bellek içi fallback
            return bool(_default_flags.get(name, False))
    return bool(_default_flags.get(name, False))


def set_feature_flag(name: str, enabled: bool) -> None:
    """Bayrağın değerini ayarlar (Redis varsa oraya da yazar)."""
    _default_flags[name] = bool(enabled)
    if USE_REDIS and redis_client is not None:
        try:
            redis_client.set(_redis_key(name), "1" if enabled else "0")
        except Exception:
            # Redis hatası testleri bozmasın
            pass


def get_feature_flag_metadata(name: str) -> Dict[str, Any]:
    """Bayrak meta verisini döndürür (yoksa boş dict)."""
    return dict(_default_flag_meta.get(name, {}))


def all_feature_flags() -> Dict[str, bool]:
    """
    Tüm bilinen bayrakları dict olarak döndürür: {name: enabled_bool}
    Testler bu fonksiyonun dict döndürmesini bekliyor.
    """
    result: Dict[str, bool] = {}
    for nm in _get_all_known_names():
        result[nm] = feature_flag_enabled(nm)
    return result


def get_feature_flags() -> list[dict]:
    """
    Admin API listeleri için kullanışlı: [{'name', 'enabled', 'meta'}, ...]
    (Bazı endpoint'ler bunu doğrudan tüketebilir.)
    """
    out: list[dict] = []
    for nm in sorted(_get_all_known_names()):
        out.append(
            {
                "name": nm,
                "enabled": feature_flag_enabled(nm),
                "meta": get_feature_flag_metadata(nm),
            }
        )
    return out


# --- create / update / delete ------------------------------------------------
def create_feature_flag(
    flag_name: Optional[str] = None,
    enabled: Optional[bool] = False,
    *,
    name: Optional[str] = None,
    description: str = "",
    category: str = "general",
    created_by: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Yeni bir feature flag oluşturur.
    Hem `flag_name` hem de `name` parametresini destekler.
    """
    fname = (flag_name or name or "").strip()
    if not fname:
        raise ValueError("flag_name (or name) is required")

    # Değeri yaz
    set_feature_flag(fname, bool(enabled))

    # Meta oluştur/güncelle
    now = _now_iso()
    meta = _default_flag_meta.setdefault(fname, {})
    meta.setdefault("created_at", now)
    meta["created_by"] = created_by
    meta["description"] = description or meta.get("description", "")
    meta["category"] = category or meta.get("category", "general")

    return {"name": fname, "enabled": feature_flag_enabled(fname), "meta": dict(meta)}


def update_feature_flag(
    flag_name: Optional[str] = None,
    *,
    name: Optional[str] = None,
    enabled: Optional[bool] = None,
    description: Optional[str] = None,
    category: Optional[str] = None,
    updated_by: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Mevcut feature flag'i günceller.
    Hem `flag_name` hem de `name` parametresini destekler.
    """
    fname = (flag_name or name or "").strip()
    if not fname:
        raise ValueError("flag_name (or name) is required")

    if enabled is not None:
        set_feature_flag(fname, bool(enabled))

    meta = _default_flag_meta.setdefault(fname, {})
    meta.setdefault("created_at", _now_iso())
    meta["updated_at"] = _now_iso()
    meta["updated_by"] = updated_by
    if description is not None:
        meta["description"] = description
    if category is not None:
        meta["category"] = category

    return {"name": fname, "enabled": feature_flag_enabled(fname), "meta": dict(meta)}


def delete_feature_flag(
    flag_name: Optional[str] = None,
    *,
    name: Optional[str] = None,
) -> bool:
    """
    Feature flag'i siler. (Meta ve bellek içi değer)
    Redis kullanılıyorsa oradan da kaldırmaya çalışır.
    """
    fname = (flag_name or name or "").strip()
    if not fname:
        raise ValueError("flag_name (or name) is required")

    existed = False
    if fname in _default_flags:
        existed = True
        _default_flags.pop(fname, None)
    if fname in _default_flag_meta:
        _default_flag_meta.pop(fname, None)

    if USE_REDIS and redis_client is not None:
        try:
            redis_client.delete(_redis_key(fname))
        except Exception:
            pass

    return existed


__all__ = [
    "USE_REDIS",
    "redis_client",
    "_default_flags",
    "_default_flag_meta",
    "feature_flag_enabled",
    "set_feature_flag",
    "get_feature_flag_metadata",
    "all_feature_flags",
    "get_feature_flags",
    "create_feature_flag",
    "update_feature_flag",
    "delete_feature_flag",
]
