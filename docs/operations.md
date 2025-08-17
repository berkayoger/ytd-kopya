# Operations / Observability

## Metrics
Prometheus formatında `/metrics` (opsiyonel Basic Auth + IP allowlist).

### Sayaçlar
- `draks_decision_requests_total{status}`
  - 200, 400, 403, 429, 500 gibi durumlar.
- `draks_copy_requests_total{status}`
- `draks_errors_total{type}`
  - `type`: `decision`, `copy`, vb.

### Histogram
- `draks_request_latency_seconds{route}`
  - `route`: `draks_decision_run`, `draks_copy_evaluate` vb.
  - Bucket’ları `.env` üzerinden `METRICS_LATENCY_BUCKETS` ile özelleştirilebilir.

## Request-ID
Her isteğe `X-Request-ID` header’ı döner. İstek yoksa sunucu üretir.
Loglar `request_id`, `user_id`, `latency_sec` gibi alanlarla structured olarak yazılır.

## Güvenlik
- IP allowlist: `METRICS_ALLOW_IPS=10.0.0.1,10.0.0.2`
- Basic Auth: `METRICS_BASIC_AUTH_USER=metrics` ve `METRICS_BASIC_AUTH_PASS=secret`

## Örnek Prometheus scrape
```yaml
scrape_configs:
  - job_name: ytd-backend
    metrics_path: /metrics
    static_configs:
      - targets: ['backend:5000']
```

## Grafana önerileri
- Panel: Latency p95/p99 (`histogram_quantile` ile)
- Panel: Success ratio = 200 / (200+4xx+5xx)
- Panel: Errors by type (`draks_errors_total{type}` rate())

## Admin Test Çalıştırma
- Endpoint: `POST /api/admin/tests/run` (sadece admin, rate-limit 6/saat)
- Status: `GET /api/admin/tests/status` (sadece admin) → `{ "allowed": true|false }`
- Env toggle: `ALLOW_ADMIN_TEST_RUN=true` (default: false)
- Request body:
```json
{ "suite": "unit|smoke|all", "extra": "-k mypattern" }
```
- Response: exit_code, özet, stdout/stderr (kısaltılmış) içerir.

### Güvenlik Sertleştirme
- Alt süreç çalışma dizini repo kökü ile sınırlandırılmıştır.
- Alt sürece aktarılan environment beyaz listelidir (PATH, PYTHONPATH, FLASK_ENV vb.). Gizli anahtarlar aktarılmaz.

## Batch İşleri (Operasyon)

### Env
- `DRAKS_BATCH_ENABLED=true`
- `BATCH_MAX_SYMBOLS=50`
- `BATCH_MAX_CANDLES=500`
- `BATCH_RATE_LIMIT=2/hour`
- `BATCH_JOB_TIMEOUT=300`
- `OHLCV_CACHE_TTL=600`, `DECISION_CACHE_TTL=600`

### Metrikler
- `draks_batch_submit_total{status}`
- `draks_batch_items_total{asset,status}`
- `draks_batch_job_duration_seconds`
- `draks_ohlcv_cache_hit_total{asset}` / `draks_ohlcv_cache_miss_total{asset}`

### Alarm Önerileri
- Submit error rate artışı
- Job duration p95 > 300s
- Cache miss oranı %80'i geçerse veri kaynakları yavaş/arıza olabilir

### Güvenlik
- Rate-limit (BATCH_RATE_LIMIT) sıkı tutun
- Feature-flag ile kapatma: `draks_batch`
- Redis TTL'ler zorunlu, key'ler `draks:*` namespace'inde
