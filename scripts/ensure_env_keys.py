#!/usr/bin/env python3
"""
Idempotent .env.example anahtar ekleyici.
 - Mevcut anahtarları asla değiştirmez.
 - Eksik olanları dosyanın SONUNA ekler (yorum başlıklarıyla).
Kullanım:
  python scripts/ensure_env_keys.py --check   # sadece raporla, exit 1 eksik varsa
  python scripts/ensure_env_keys.py --apply   # eksikleri ekle ve kaydet
"""
import argparse, os, sys, re, textwrap
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ENV_EXAMPLE = REPO_ROOT / ".env.example"

# Projeye eklediğimiz güvenlik ve billing özellikleri için gerekli anahtarlar
REQUIRED_KEYS = {
    # Secrets & JWT
    "SECRET_PROVIDER": "aws",  # aws | azure | env
    "JWT_SECRET_NAME": "jwt-secret",
    "AZURE_KEY_VAULT_URL": "https://your-vault.vault.azure.net/",
    "ACCESS_TOKEN_EXPIRES_MINUTES": "15",
    "REFRESH_TOKEN_EXPIRES_DAYS": "30",
    "JWT_KEY_VERSION": "1",
    "JWT_ROTATION_INTERVAL_DAYS": "30",
    "CSRF_SECRET": "change-this-long-random-string",
    "TOTP_ISSUER_NAME": "YTD-Crypto",
    "EMAIL_FROM": "noreply@example.com",
    # DB/Redis (önceden varsa dokunulmaz)
    "DATABASE_SSL_MODE": "require",
    "DATABASE_CONNECTION_POOL_SIZE": "20",
    "REDIS_URL": "redis://localhost:6379",
    "REDIS_SSL_ENABLED": "true",
    # Security headers / CORS / Rate limit
    "SECURE_HEADERS_ENABLED": "true",
    "HSTS_MAX_AGE": "31536000",
    "CSP_POLICY": "default-src 'self'; script-src 'self' 'unsafe-inline'",
    "SECURITY_CORS_ALLOWED_ORIGINS": "http://localhost:3000,https://app.example.com",
    "SECURITY_CORS_ALLOW_CREDENTIALS": "false",
    "RATE_LIMIT_DEFAULT": "100/minute",
    "LOGIN_RATE_LIMIT": "10/minute",
    "LOGIN_MAX_ATTEMPTS": "5",
    "LOGIN_LOCKOUT_DURATION_MINUTES": "15",
    # Security wrapper
    "WSGI_APP": "app.secure_app:app",
    # Billing / Site
    "BILLING_PROVIDER": "stripe",  # stripe | craftgate
    "SITE_URL": "https://app.example.com",
    "CHECKOUT_SUCCESS_PATH": "/billing/success",
    "CHECKOUT_CANCEL_PATH": "/billing/cancel",
    # Stripe
    "STRIPE_SECRET_KEY": "sk_test_xxx",
    "STRIPE_WEBHOOK_SECRET": "whsec_xxx",
    "STRIPE_BILLING_PORTAL_RETURN_URL": "https://app.example.com/account",
    # Craftgate (opsiyonel)
    "CRAFTGATE_API_KEY": "your-key",
    "CRAFTGATE_SECRET_KEY": "your-secret",
    "CRAFTGATE_MERCHANT_ID": "12345",
    "CRAFTGATE_WEBHOOK_SECRET": "your-webhook-secret",
    # Plan seed
    "SEED_PLANS": "BASIC:999:TRY:month,PRO:2999:TRY:month,PREMIUM:4999:TRY:month",
}

SECTION_HEADER = textwrap.dedent("""\

# ================= Added by ensure_env_keys.py =================
# Aşağıdaki anahtarlar yeni özellikler için gereklidir. Üretimde gerçek sırları
# AWS Secrets Manager / Azure Key Vault üzerinden sağlayın.
""")

KEY_ORDER = [
    # Görsel blok sırası (mantıksal gruplama)
    "SECRET_PROVIDER","JWT_SECRET_NAME","AZURE_KEY_VAULT_URL",
    "ACCESS_TOKEN_EXPIRES_MINUTES","REFRESH_TOKEN_EXPIRES_DAYS",
    "JWT_KEY_VERSION","JWT_ROTATION_INTERVAL_DAYS","CSRF_SECRET","TOTP_ISSUER_NAME","EMAIL_FROM",
    "DATABASE_SSL_MODE","DATABASE_CONNECTION_POOL_SIZE",
    "REDIS_URL","REDIS_SSL_ENABLED",
    "SECURE_HEADERS_ENABLED","HSTS_MAX_AGE","CSP_POLICY",
    "SECURITY_CORS_ALLOWED_ORIGINS","SECURITY_CORS_ALLOW_CREDENTIALS",
    "RATE_LIMIT_DEFAULT","LOGIN_RATE_LIMIT","LOGIN_MAX_ATTEMPTS","LOGIN_LOCKOUT_DURATION_MINUTES",
    "WSGI_APP",
    "BILLING_PROVIDER","SITE_URL","CHECKOUT_SUCCESS_PATH","CHECKOUT_CANCEL_PATH",
    "STRIPE_SECRET_KEY","STRIPE_WEBHOOK_SECRET","STRIPE_BILLING_PORTAL_RETURN_URL",
    "CRAFTGATE_API_KEY","CRAFTGATE_SECRET_KEY","CRAFTGATE_MERCHANT_ID","CRAFTGATE_WEBHOOK_SECRET",
    "SEED_PLANS",
]

def parse_keys(lines):
    env = {}
    for ln in lines:
        if ln.strip().startswith("#"): continue
        m = re.match(r'^([A-Z0-9_]+)=(.*)$', ln.strip())
        if m:
            env[m.group(1)] = m.group(2)
    return env

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="Eksik anahtarları ekle ve kaydet")
    ap.add_argument("--check", action="store_true", help="Sadece doğrula; eksik varsa exit 1")
    ap.add_argument("--file", default=str(ENV_EXAMPLE), help="Hedef .env.example yolu")
    args = ap.parse_args()

    path = Path(args.file)
    if not path.exists():
        # Dosya yoksa yeni oluştur
        base = []
    else:
        base = path.read_text(encoding="utf-8").splitlines(keepends=False)
    existing = parse_keys(base)
    missing = [k for k in KEY_ORDER if k not in existing]

    if args.check and missing:
        print("Eksik .env keys:", ", ".join(missing))
        sys.exit(1)
    if args.check:
        print("Tüm gerekli .env anahtarları mevcut.")
        return

    if not args.apply:
        print("Hiçbir işlem yapılmadı. --apply ile yazdırabilirsiniz.")
        return

    # Yazım: mevcut içeriği koru, sona kendi bloğumuzu ekle
    out = list(base)
    if missing:
        out.append(SECTION_HEADER.rstrip("\n"))
        for k in KEY_ORDER:
            if k in existing: continue
            v = REQUIRED_KEYS[k]
            out.append(f"{k}={v}")
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"✔ Güncellendi: {path} (eklenen anahtarlar: {', '.join(missing) if missing else 'yok'})")

if __name__ == "__main__":
    main()
