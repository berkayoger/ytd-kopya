# Admin Batch UI

Yeni admin sayfası:

- Route: `/admin/batch`
- Form alanları: asset, timeframe, limit, symbols (textarea)
- Progress bar: status polling `/api/draks/batch/status/{jobId}`
- Result listesi: `/api/draks/batch/results/{jobId}` filtreleriyle

Giriş için JWT + (opsiyonel) API key gereklidir.
