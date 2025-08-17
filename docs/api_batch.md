# Batch API (Güvenlik Sertleştirmeli)

## Özellikler
- Input doğrulama (asset/timeframe/symbol)
- IP allowlist (BATCH_IP_ALLOWLIST)
- Büyük batch için admin onayı (BATCH_ADMIN_APPROVAL_THRESHOLD)
- Opsiyonel 2FA zorunluluğu (BATCH_REQUIRE_2FA)
- Rate limit (`BATCH_RATE_LIMIT`, güvenli parser ile)
- Anomali tespiti (kullanıcı/IP başına kaydırmalı pencere)
- Celery işlerinde zaman limiti ve RAM koruması (fail-fast)

## Endpoints
### POST /api/batch/submit
Body:
```json
{ "symbols": ["BTC/USDT","ETH/USDT"], "timeframe": "1h", "asset": "crypto" }
```
Yanıt:
```json
{ "job_id": "celery-uuid", "count": 2 }
```

### GET /api/batch/status/{job_id}
```json
{ "id": "...", "state": "PENDING|STARTED|SUCCESS|FAILURE", "ready": true|false }
```

### GET /api/batch/results/{job_id}
İş hazır değilse 202 döner; hazırsa `{"items":[...], "count":N}`.

## Admin Onay
### POST /api/admin/batch/approval/grant
```json
{ "user_id": "123", "ttl_s": 3600 }
```
### POST /api/admin/batch/approval/revoke
```json
{ "user_id": "123" }
```

## Konfig
- `DRAKS_BATCH_ENABLED=true`
- `BATCH_MAX_SYMBOLS=50`, `BATCH_MAX_CANDLES=500`
- `BATCH_RATE_LIMIT=2/hour`
- `BATCH_JOB_TIMEOUT=300`
- `OHLCV_CACHE_TTL=600`, `DECISION_CACHE_TTL=600`
- `BATCH_REQUIRE_2FA=false`
- `BATCH_IP_ALLOWLIST=10.0.0.1,10.0.0.2`
- `BATCH_ADMIN_APPROVAL_THRESHOLD=25`
- `CELERY_WORKER_MEMORY_LIMIT_MB=512` (worker flag ile de sınırlandırın: `--max-memory-per-child`)
- `ANOMALY_WINDOW_SEC=900`, `ANOMALY_MAX_SUBMITS_PER_WINDOW=5`
