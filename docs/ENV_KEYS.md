# Zorunlu Ortam Anahtarları (Auth & Billing)

Bu projede güvenlik ve abonelik için gerekli başlıca anahtarlar:

## Güvenlik / JWT
- `SECRET_PROVIDER` (aws|azure|env)
- `JWT_SECRET_NAME`, `AZURE_KEY_VAULT_URL` (azure için)
- `ACCESS_TOKEN_EXPIRES_MINUTES=15`, `REFRESH_TOKEN_EXPIRES_DAYS=30`
- `JWT_KEY_VERSION`, `JWT_ROTATION_INTERVAL_DAYS`
- `CSRF_SECRET`, `TOTP_ISSUER_NAME`

## Ağ & Başlıklar
- `SECURE_HEADERS_ENABLED`, `HSTS_MAX_AGE`, `CSP_POLICY`
- `SECURITY_CORS_ALLOWED_ORIGINS`, `SECURITY_CORS_ALLOW_CREDENTIALS`
- `RATE_LIMIT_DEFAULT`, `LOGIN_RATE_LIMIT`, `LOGIN_MAX_ATTEMPTS`, `LOGIN_LOCKOUT_DURATION_MINUTES`
- `WSGI_APP=app.secure_app:app`

## Billing
- `BILLING_PROVIDER=stripe|craftgate`
- `SITE_URL`, `CHECKOUT_SUCCESS_PATH`, `CHECKOUT_CANCEL_PATH`
- Stripe: `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_BILLING_PORTAL_RETURN_URL`
- Craftgate: `CRAFTGATE_API_KEY`, `CRAFTGATE_SECRET_KEY`, `CRAFTGATE_MERCHANT_ID`, `CRAFTGATE_WEBHOOK_SECRET`
- `SEED_PLANS` örn. `BASIC:999:TRY:month,PRO:2999:TRY:month`

> `.env.example` dosyanız farklı ise `scripts/ensure_env_keys.py --apply` komutu eksikleri **sona ekler**, mevcut değerleri **asla değiştirmez**.
