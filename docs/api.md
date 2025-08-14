# API Documentation

Bu doküman kimliği doğrulanmış API uçlarını özetler. JWT Bearer zorunludur (aksi belirtilmedikçe).

## GET /api/limits/status

Returns the current user's subscription plan and usage limits.

### Authentication
- JWT Bearer token required.

### Response
- **200 OK**
```
{
  "plan": "premium",
  "limits": {
    "daily_requests": {"used": 45, "max": 100, "percent": 45},
    "monthly_requests": {"used": 1200, "max": 3000, "percent": 40}
  },
  "reset_at": "2025-02-01T00:00:00",

  "custom_features": {
    "beta_mode": true,
    "extra_quota": 250
  }
}
```
### Notes
- `reset_at`: ISO-8601 UTC timestamp for when monthly limits reset.
- Reset day is configurable via environment variable `LIMITS_RESET_DAY` (1–28).
  If not set, it defaults to the 1st day of each month.
- `custom_features`: Optional per-user overrides/feature flags (object). Values may be booleans,
  numbers or strings. Clients should display them as read-only hints.

### Error Responses
- **401 Unauthorized**: `{ "error": "Kullanıcı bulunamadı." }`
- **403 Forbidden**: `{ "error": "Özellik kapalı." }`
- **500 Internal Server Error**: `{ "error": "Limitler alınamadı." }`

---

## POST /api/draks/decision/run

DRAKS karar motorunu çalıştırır. `draks`/`draks_enabled` feature-flag’i açık olmalıdır.

### Auth
- JWT Bearer zorunlu.
- Plan limit anahtarı: `draks_decision`

### Request body
```json
{
  "symbol": "BTC/USDT",
  "timeframe": "1h",
  "limit": 500,
  "candles": [
    { "ts": 1710000000, "open": 100, "high": 110, "low": 95, "close": 105, "volume": 1234 }
  ]
}
```
Notlar:
- `candles` sağlanırsa motor bu veriyi kullanır. Sağlanmazsa (ve ortam destekliyorsa) ccxt ile borsadan çekmeye çalışır.
- `ts` epoch saniye/ms veya ISO-8601 olabilir.

### Response (200)
```json
{
  "symbol": "BTC/USDT",
  "timeframe": "1h",
  "decision": "LONG | SHORT | HOLD",
  "direction": 1,
  "score": 0.123,
  "position_pct": 0.018,
  "stop": 102.1,
  "take_profit": 108.9,
  "horizon_days": 15,
  "regime_probs": { "bull": 0.41, "bear": 0.18, "volatile": 0.22, "range": 0.19 },
  "weights": { "trend": 0.45, "momentum": 0.35, "meanrev": 0.20 },
  "reasons": ["EMA20-EMA50","slope","RSI","MACD_hist"],
  "as_of": "2025-08-14T20:00:00Z"
}
```

### Hatalar
- **403**: `{ "error": "Özellik şu anda devre dışı." }`
- **400**: `{ "error": "yetersiz veri" }`
- **429**: plan limiti aşıldı.
- **500**: beklenmeyen hata.

---

## POST /api/draks/copy/evaluate

Kopya (copy-trading) senaryosunda lider sinyali DRAKS ile doğrular; yeşil ışık ve ölçek önerir.

### Auth
- JWT Bearer zorunlu.
- Plan limit anahtarı: `draks_copy`

### Request body
```json
{
  "symbol": "BTC/USDT",
  "side": "BUY",                  // veya SELL
  "size": 1000,                   // opsiyonel nominal büyüklük
  "timeframe": "1h",
  "candles": [ /* opsiyonel */ ]
}
```

### Response (200)
```json
{
  "greenlight": true,
  "scaled_size": 640.5,           // size * ölçek faktörü (0..1), yoksa null
  "draks": { /* decision.run cevabı */ }
}
```

### Hatalar
403 (flag), 429 (limit), 500 (sunucu hatası).
