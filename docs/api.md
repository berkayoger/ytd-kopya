# API Documentation

Bu doküman kimliği doğrulanmış API uçlarını özetler. JWT Bearer zorunludur (aksi belirtilmedikçe).

## Quickstart / Setup

1) **Feature flag’i açın**  
   - `draks` **veya** `draks_enabled` bayrağını **true** yapın (Admin Feature Flags veya Redis anahtarı: `feature_flag:draks="true"`).

2) **Motor**  
   - **Entegre minimal motor** (varsayılan): Ek servis gerekmez. `/api/draks/health` ile kontrol edin.
   - **Harici FastAPI motoru** (opsiyonel): `DRAKS_ENGINE_URL` ayarlayın (örn. `http://draks-engine:8000`) ve motoru ayağa kaldırın.

3) **Test**  
   - `GET /api/draks/health` → `{"status":"ok","enabled":true}` beklenir.
   - `POST /api/draks/decision/run` → örnek gövdeyle karar dönmelidir.

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

## GET /api/draks/health

DRAKS entegrasyonu için basit sağlık kontrolü.

### Auth
- Gerekli değil.

### Response (200)
```json
{ "status": "ok", "enabled": true }
```
`status`: ok | degraded | error

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
  "size": 1000,                   // opsiyonel nominal büyüklük (>= 0, sayısal)
  "timeframe": "1h",
  "limit": 500,                   // opsiyonel, candles yoksa ccxt ile çekilecek mum sayısı
  "candles": [ /* opsiyonel, sağlanırsa ccxt'e ihtiyaç yok */ ]
}
```

### Response (200)
```json
{
  "greenlight": true,
  "scale_factor": 0.64,           // 0..1 arası ölçek katsayısı
  "scaled_size": 640.5,           // size * scale_factor, size yoksa null
  "draks": { /* decision.run cevabı */ }
}
```

Ölçek, motorun döndürdüğü skordan türetilir. Daha gelişmiş ve rejime duyarlı
filtreleme için `draks_advanced` bayrağı veya `DRAKS_ADVANCED=true`
ortam değişkeni kullanılabilir.

Canlı modda daha sıkı risk kapakları `DRAKS_LIVE_MODE=true` ile etkinleşir.
Bu mod yalnızca ölçek tavanını düşürür; plan ve flag kontrolleri aynen geçerlidir.

### Hatalar
-403 (flag), 429 (limit), 500 (sunucu hatası). +- 400:

Geçersiz side. BUY veya SELL olmalı.


size sayısal olmalı / size negatif olamaz


limit sayısal olmalı


candles sağlanmalı veya ccxt kurulmalı


yetersiz veri

---

## GET /api/admin/draks/decisions  (ADMIN)
Son DRAKS kararlarını sayfalı döndürür.

Query:
- `page` (varsayılan 1), `limit` (<=100), `symbol` (opsiyonel tam eşleşme)

Yanıt:
```json
{
  "items": [
    { "id": 1, "symbol": "BTC/USDT", "decision": "LONG", "position_pct": 0.018, "stop": 102.1, "take_profit": 108.9, "created_at": "2025-08-14T20:00:00Z" }
  ],
  "meta": { "page": 1, "limit": 25, "total": 123 }
}
```

## GET /api/admin/draks/signals  (ADMIN)
Son DRAKS sinyal skorlarını sayfalı döndürür.

Yanıt:
```json
{
  "items": [
    { "id": 10, "symbol": "ETH/USDT", "timeframe": "1h", "score": 0.12, "decision": "HOLD", "created_at": "2025-08-14T20:10:00Z" }
  ],
  "meta": { "page": 1, "limit": 25, "total": 321 }
}
```
