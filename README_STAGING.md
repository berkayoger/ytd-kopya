# Staging CI/CD Kılavuzu (Kısa)

## 1) Sunucu Hazırlığı
```bash
sudo apt-get update && sudo apt-get install -y docker.io docker-compose-plugin
sudo usermod -aG docker $USER
mkdir -p ~/apps/ytd-kopya && cd ~/apps/ytd-kopya
# Repo bu dizine klonlanmalı (secrets.STAGING_PROJECT_DIR burayı göstermeli)
# .env.staging dosyasını oluştur:
cp .env.example .env.staging
# Değerleri düzenle (STAGING_FQDN, SECRET_KEY, vb.)
```

## 2) GitHub Secrets
- `STAGING_SSH_HOST`
- `STAGING_SSH_USER`
- `STAGING_SSH_KEY` (private key)
- `STAGING_PROJECT_DIR` (örn: `/home/ubuntu/apps/ytd-kopya`)

## 3) Çalışma Mantığı
- Push → `main` → test → iki imaj build → GHCR push → SSH ile sunucuda
  `docker compose -f docker-compose.staging.yml up -d`.

### Önemli Not (image adları)
- `docker-compose.staging.yml` image adlarını **env üzerinden** alır:
  - `BACKEND_IMAGE` (zorunlu) → workflow deploy adımı export eder.
  - `FRONTEND_IMAGE` (opsiyonel) → frontend imajı varsa export edilir, yoksa `ui` profili kapatılır.
- Sunucuda `GITHUB_REPOSITORY` tanımlamanıza gerek **yoktur**.


## 4) Health Endpoint’leri
- `backend/wsgi.py` mevcut uygulamayı otomatik import etmeye çalışır:
  `backend.app:create_app`, `backend.app:app`, `app:create_app`, `app:app`.
- Bulamazsa geçici bir app ile `/healthz`=200, `/readiness`=503 döner.
- Gerçek app modül yolun farklıysa `APP_IMPORT_CANDIDATES` değişkenine ekle.

### CI için “safe mode”
- CI smoke testlerinde **SAFE_HEALTH_MODE=true** verilirse `wsgi` ağır importları atlar ve
  yalnızca `/healthz` ve `/readiness` sunan minimal app’i başlatır.
- Bu mod prod/staging’de **kullanılmamalı**; sadece CI doğrulama amacıyla vardır.
