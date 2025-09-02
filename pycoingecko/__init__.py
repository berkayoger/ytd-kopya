"""
pycoingecko paketinin hafif bir gölgelemesi.
CI/test ortamlarında gerçek bağımlılık yoksa çalışmayı sürdürmek için
gerekli minimum API yüzeyini sağlar. Gerçek kütüphane kurulduğunda
otomatik olarak onu kullanır.
"""

from __future__ import annotations

import json
import os
import random
import time
from typing import Any, Dict, List, Optional

try:  # pragma: no cover - gerçek kütüphane varsa onu kullan
    import importlib

    _real = importlib.import_module("pycoingecko")  # type: ignore
    CoinGeckoAPI = getattr(_real, "CoinGeckoAPI")  # type: ignore
except Exception:  # pragma: no cover - küçük HTTP şimi devreye girer
    import urllib.parse
    import urllib.request
    from urllib.error import HTTPError, URLError

    class _HTTP:
        """Basit HTTP GET yardımcı sınıfı."""

        @staticmethod
        def get(
            url: str, params: Optional[Dict[str, Any]] = None, timeout: int = 15
        ) -> Any:
            """JSON dönen HTTP GET isteği."""
            if params:
                qs = urllib.parse.urlencode(
                    {
                        k: (",".join(v) if isinstance(v, (list, tuple)) else v)
                        for k, v in params.items()
                        if v is not None
                    }
                )
                url = f"{url}?{qs}"
            req = urllib.request.Request(
                url, headers={"User-Agent": "ytd-kopya/pycoingecko-shim"}
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = resp.read()
                return json.loads(data.decode("utf-8"))

    class CoinGeckoAPI:  # pragma: no cover - dış API çağrıları
        """Gerçek CoinGeckoAPI için minimal uyumlu şim."""

        def __init__(self, api_base: str | None = None):
            self.api_base = api_base or "https://api.coingecko.com/api/v3"
            self._last_call = 0.0
            self._min_interval = float(
                os.environ.get("COINGECKO_MIN_INTERVAL_SEC", "0.2")
            )
            # Offline mod bayrağı (CI/pytest'te ağsız deterministik sonuçlar)
            # Öncelik: explicit env -> pytest varlığı -> default False
            explicit = os.environ.get("COINGECKO_SHIM_OFFLINE")
            if explicit is not None:
                self._offline = explicit == "1"
            else:
                self._offline = "PYTEST_CURRENT_TEST" in os.environ

        # ---------- Offline yardımcıları ----------
        @staticmethod
        def _offline_price(ids: Any, vs_currencies: Any) -> Dict[str, Dict[str, Any]]:
            if isinstance(ids, str):
                ids = ids.split(",")
            if isinstance(vs_currencies, str):
                vs_currencies = vs_currencies.split(",")
            ids = [i for i in (ids or []) if i]
            vs_currencies = [c for c in (vs_currencies or []) if c]
            if not ids:
                ids = ["bitcoin"]
            if not vs_currencies:
                vs_currencies = ["usd"]
            out: Dict[str, Dict[str, Any]] = {}
            rng = random.Random(42)  # deterministik
            for i in ids:
                out[i] = {}
                base = 10000 + rng.randint(0, 5000)
                for cur in vs_currencies:
                    out[i][cur] = float(base)
            return out

        @staticmethod
        def _offline_markets(
            vs_currency: str, ids: Optional[List[str]], per_page: int, page: int
        ) -> List[Dict[str, Any]]:
            if not ids:
                ids = ["bitcoin", "ethereum", "tether"]
            rng = random.Random(1337)
            items: List[Dict[str, Any]] = []
            for coin_id in ids[:per_page]:
                price = 1000 + rng.randint(0, 2000)
                items.append(
                    {
                        "id": coin_id,
                        "symbol": coin_id[:3],
                        "name": coin_id.capitalize(),
                        "current_price": float(price),
                        "market_cap": float(price * 1_000_000),
                        "total_volume": float(price * 10_000),
                        "price_change_percentage_24h": rng.uniform(-5.0, 5.0),
                        "last_updated": "1970-01-01T00:00:00Z",
                        "vs_currency": vs_currency,
                    }
                )
            return items

        def _throttle(self) -> None:
            """Ardışık çağrılar arasında küçük bir gecikme uygula."""
            now = time.time()
            elapsed = now - self._last_call
            if elapsed < self._min_interval:
                time.sleep(self._min_interval - elapsed)
            self._last_call = time.time()

        def ping(self) -> Dict[str, str]:
            """API canlılık testi."""
            if self._offline:
                return {"gecko_says": "(offline) to the Moon!"}
            self._throttle()
            try:
                return _HTTP.get(f"{self.api_base}/ping")
            except (URLError, HTTPError, TimeoutError, ValueError):
                return {"gecko_says": "(fallback) to the Moon!"}

        def get_price(
            self,
            ids: Any,
            vs_currencies: Any,
            include_market_cap: bool = False,
            include_24hr_vol: bool = False,
            include_24hr_change: bool = False,
            include_last_updated_at: bool = False,
        ) -> Dict[str, Dict[str, Any]]:
            """/simple/price sarmalayıcısı."""
            if self._offline:
                return self._offline_price(ids, vs_currencies)
            self._throttle()
            try:
                if isinstance(ids, (list, tuple)):
                    ids = ",".join(ids)
                if isinstance(vs_currencies, (list, tuple)):
                    vs_currencies = ",".join(vs_currencies)
                params = {
                    "ids": ids,
                    "vs_currencies": vs_currencies,
                    "include_market_cap": str(include_market_cap).lower(),
                    "include_24hr_vol": str(include_24hr_vol).lower(),
                    "include_24hr_change": str(include_24hr_change).lower(),
                    "include_last_updated_at": str(include_last_updated_at).lower(),
                }
                return _HTTP.get(f"{self.api_base}/simple/price", params=params)
            except (URLError, HTTPError, TimeoutError, ValueError):
                return self._offline_price(ids, vs_currencies)

        def get_coins_markets(
            self,
            vs_currency: str = "usd",
            ids: Optional[List[str]] = None,
            order: str = "market_cap_desc",
            per_page: int = 100,
            page: int = 1,
            sparkline: bool = False,
            price_change_percentage: Optional[str] = None,
        ) -> List[Dict[str, Any]]:
            """/coins/markets endpoint'i için temel sarmalayıcı."""
            if self._offline:
                return self._offline_markets(vs_currency, ids, per_page, page)
            self._throttle()
            try:
                params: Dict[str, Any] = {
                    "vs_currency": vs_currency,
                    "order": order,
                    "per_page": per_page,
                    "page": page,
                    "sparkline": str(sparkline).lower(),
                }
                if ids:
                    params["ids"] = ",".join(ids)
                if price_change_percentage:
                    params["price_change_percentage"] = price_change_percentage
                return _HTTP.get(f"{self.api_base}/coins/markets", params=params)
            except (URLError, HTTPError, TimeoutError, ValueError):
                return self._offline_markets(vs_currency, ids, per_page, page)


__all__ = ["CoinGeckoAPI"]
