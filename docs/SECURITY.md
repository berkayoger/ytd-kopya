# Security Playbook (YTD-Kopya)

Bu döküman prod-grade güvenlik için operasyon adımlarını içerir.

## 1) Secrets Yönetimi
- **Asla** `.env` commit etmeyin (bkz. `.gitignore`).
- Prod/staging sırları **AWS Secrets Manager** veya **Azure Key Vault** üzerinde tutulur.
- JWT için `JWT_SECRET_NAME=jwt-secret` ismi kullanılır, versiyonlama **secret versiyonları** üzerinden yapılır.

### JWT Anahtar Rotasyonu (30 günde bir)
1. Yeni versiyonu secret manager’a yazın (CI/CD veya `scripts/rotate_jwt_secret.py`):
2. Uygulama konfiginde `JWT_KEY_VERSION` değerini **+1** artırın.
3. Eski refresh token’lar **grace** penceresinde (decode cur+prev) çalışır; otomatik yenilenecek ve revoke edilecektir.

## 2) Token Stratejisi
- Access token: **15 dk**
- Refresh token: **30 gün**, **rotate-on-use**, eski refresh **revoke** (Redis JTI blacklist).
- Çıkış/cihaz iptali: ilgili access/refresh `jti` değerleri **revoke** edilir.

## 3) Giriş Güvenliği
- **Rate limit**: global `RATE_LIMIT_DEFAULT` + login özel `LOGIN_RATE_LIMIT`.
- **Lockout**: üst üste başarısız girişte geçici kilit (Redis).
- Parola politikası: minimum 12, karmaşıklık, tekrar blok, **pwned** kontrolü.
- **2FA** (TOTP) kritik işlemlerde zorunlu.

## 4) Web Güvenlik Başlıkları
- HSTS (preload), **katı CSP**, `X-Frame-Options=DENY`, `X-Content-Type-Options=nosniff`, `Referrer-Policy=strict-origin-when-cross-origin`, `Permissions-Policy`.

## 5) CSRF
- Cookie tabanlı oturum varsa CSRF token zorunlu; saf Bearer token’lı API çağrılarında CSRF aranmaz.
- Token yapısı: HMAC(secret) + timestamp + nonce + session_id.

## 6) CI / Supply Chain
- **SBOM** oluştur (CycloneDX).
- `pip-audit` ve `pip check` zorunlu.
- Dependabot + Code Scanning önerilir.

## 7) Olay Günlüğü
- Başarısız giriş/lockout, token-reuse, admin işlemleri ve gizlilik ihlali girişimleri alarm üretmelidir.

## 8) Veri Koruma
- PII sınıflandırma, saklama süresi, “right-to-erasure” uç noktaları ve log masking uygulanmalıdır.

