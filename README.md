# YTD-Kopya

> **Security-hardening aktif**  
> Prod/staging kurulumunda WSGI entrypoint olarak **`app.secure_app:app`** kullanın. Bu sarmalayıcı mevcut Flask uygulamasını otomatik bulur ve:
> - CORS allowlist,
> - Global rate limit + login özel limit,
> - HSTS/CSP ve temel güvenlik başlıkları
> katmanlarını uygular.

## Ortam Değişkenlerini Hazırlama
`.env.example` dosyanız branch’ler arasında farklı olabilir. Çatışma yaşamamak için
gerekli yeni anahtarları idempotent bir script ile ekliyoruz:

```bash
python3 scripts/ensure_env_keys.py --apply
# sadece kontrol: python3 scripts/ensure_env_keys.py --check
```

Üretimde sırları `.env` yerine **AWS Secrets Manager** veya **Azure Key Vault** üzerinden sağlayın.

## Kurulum

1. Ortam değişkenlerini `.env.example` üzerinden oluşturun.
2. Veritabanı migrasyonlarını çalıştırın.
3. Uygulamayı başlatın.

### Prod güvenlik notları (özet)
- JWT: HS512, kısa ömürlü access (15 dk), refresh (30 gün) + **rotate-on-use** ve **revoke (Redis JTI)**.
- Sırlar: **Secrets Manager/Key Vault**; `JWT_KEY_VERSION` ile rotasyon. `scripts/rotate_jwt_secret.py` aracı mevcuttur.
- Giriş güvenliği: parola politikası (Argon2id) + pwned kontrolü, brute-force lockout, route başına rate-limit.
- CSRF: Cookie tabanlı oturum kullanıyorsanız HMAC+timestamp token zorunludur.
- Web güvenliği: HSTS (preload), katı CSP, XFO=DENY, XCTO=nosniff.
- CI: `pip-audit` ve **SBOM** üretimi (`.github/workflows/security.yml`).

Bu proje Flask tabanlı bir kripto para analiz uygulamasıdır. Depo iki ana kısımdan oluşur:

* **backend/** - Flask API ve analiz servisleri
* **frontend/** - Basit HTML arayüzü

Ek olarak `scripts/` dizininde yardımcı araçlar bulunur.

Hızlı bir analiz denemek için `scripts/crypto_ta.py` dosyasını çalıştırabilirsiniz.
Bu betik CoinGecko servisine erişim olmadığında örnek verilerle teknik
analiz göstergelerini hesaplar.

Gerçek zamanlı fiyat bilgisini almak için `backend/utils/price_fetcher.py`
içindeki `fetch_current_price` fonksiyonu kullanılabilir. Ağ sorunu olduğunda
fonksiyon `None` döndürür ve görevler bunu ele alacak şekilde tasarlanmıştır.

Backend klasör yapısı aşağıdaki gibidir:

```
backend/
├── __init__.py           # create_app fonksiyonunu dışa açar
├── api/
│   ├── __init__.py       # API Blueprint tanımı
│   └── routes.py         # Analiz endpointleri
├── auth/
│   ├── __init__.py       # Auth Blueprint'i
│   └── routes.py         # Kullanıcı işlemleri
├── admin_panel/
│   ├── __init__.py       # Admin Blueprint'i
│   └── routes.py         # Yönetici paneli
├── db/
│   ├── __init__.py       # SQLAlchemy db nesnesi
│   └── models.py         # Veritabanı modelleri
├── core/
│   ├── __init__.py       # Boş
│   └── services.py       # YTD servis sınıfları
├── tasks/
│   ├── __init__.py       # Celery paket tanımı
│   └── celery_tasks.py   # Görevler
├── requirements.txt
├── .env.example
└── Dockerfile
```

Ana dizinlerin sorumluluklari:
- **api/**: REST API uc noktalari
- **auth/**: kullanici kaydi, giris ve JWT yonetimi
- **admin_panel/**: yonetici paneli rotalari
- **core/**: analiz servisleri ve is mantigi
- **db/**: SQLAlchemy modelleri
- **tasks/**: Celery gorev tanimlari
- **config.py**: ortam tabanli ayarlar
- **frontend/**: statik HTML ve JavaScript
- **migrations/**: veritabani guncelleme scriptleri
- **tests/**: otomatik testler

## Proje Mimarisi ve Teknoloji Yigini

Bu proje servis odakli bir mimariye sahiptir. Backend katmani Flask uzerinde calisir ve REST API sunar. Celery agir islemleri arka planda yurutur ve zamanlanmis gorevleri yonetir. SQLAlchemy veritabanina erisim saglar, Redis hem onbellek hem de Celery brokeri olarak kullanilir. Docker tum servislerin izole calismasini kolaylastirir. Frontend mevcutta basit bir MPA yapisindadir ancak uzun vadede React benzeri bir framework ile SPA mimarisine gecis hedeflenmektedir. Flask'in sadeligi ve Python ekosistemiyle uyumu hizli prototipleme imkani saglar.


Proje kök dizininde `wsgi.py` adlı bir çalıştırıcı dosya bulunur. Bu dosya
`backend.create_app()` fonksiyonunu kullanarak Flask uygulamasını başlatır.


## Mobil Uyumlu Panel

Admin ve kullanıcı sayfaları mobil cihazlarda da rahat kullanılabilmesi için responsive hâle getirildi. HTML dosyalarına `viewport` meta etiketi eklendi ve tablolar `overflow-x-auto` sınıfı ile yatay kaydırılabilir yapıldı. Böylece küçük ekranlarda menü ve kritik işlemler erişilebilir oldu.

## Kurulum

1. Depoyu klonlayın ve gerekli bağımlılıkları kurun:

```bash
pip install -r backend/requirements.txt
```

Flask-Migrate ile veritabanı şema değişikliklerini yönetmek için ilk kez şu adımları uygulayın:

```bash
flask db init
flask db migrate -m "initial"
flask db upgrade
```

2. `.env.example` dosyasını `.env` olarak kopyalayın ve gerekli API anahtarlarını doldurun.

## 🔐 Güvenlik Yapılandırması

Uygulamayı çalıştırmadan önce güvenlik kontrollerini yapın:

```bash
python scripts/security_check.py
```

Bu script, JWT token güvenliği, şifreleme anahtarları ve diğer güvenlik ayarlarını kontrol eder.

3. Gerekli konfigürasyon sınıfı `FLASK_ENV` değişkeni ile seçilir. Varsayılan
   değer `development`'tır. Örneğin test ortamı için:

```bash
export FLASK_ENV=testing
```

4. Uygulamayı yerel ortamda çalıştırmak için:

```bash
python wsgi.py
```

## Docker ile Çalıştırma

Docker yüklüyse projeyi şu komutla hızlıca başlatabilirsiniz:

```bash
docker-compose up --build
```

## Production Kurulumu (Gunicorn ve Nginx)

Gerçek bir sunucuda uygulamayı yayınlamak için `app.py` dosyası üzerinden
`create_app` fonksiyonunu kullanarak Gunicorn çalıştırabilirsiniz:

```bash
gunicorn -w 4 -b 127.0.0.1:5000 'app:create_app()'
```

Ardından Nginx'i ters proxy olarak yapılandırıp statik dosyaları servis
edecek şekilde ayarlayabilirsiniz. Örnek bir konfigürasyon:

```nginx
server {
    listen 80;
    server_name admin.example.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /static/ {
        alias /path/to/your/frontend/;
    }
}
```

HTTPS sertifikası için Let's Encrypt (`certbot --nginx`) ve güvenlik için UFW
kuralları eklemeniz önerilir. Uygulamanın arka planda kalıcı olarak
çalışması için Supervisor kullanılabilir.

## 🛡️ Güvenlik Özellikleri

Bu uygulama aşağıdaki güvenlik özelliklerini içerir:

- **Gelişmiş JWT Token Yönetimi**: Access ve refresh token'lar ile güvenli kimlik doğrulama
- **Token Blacklisting**: Çıkış yapıldığında token'ların geçersiz kılınması
- **Rate Limiting**: API istekleri için hız sınırlandırması
- **CSRF Koruması**: Cross-Site Request Forgery saldırılarına karşı koruma
- **Güvenlik Event Logging**: Tüm güvenlik olaylarının kayıt altına alınması
- **IP ve User Agent Analizi**: Şüpheli aktivitelerin tespit edilmesi
- **Güçlü Şifre Politikası**: Minimum güvenlik gereksinimleri
- **Session Yönetimi**: Güvenli oturum işlemleri
- **Security Headers**: XSS, CSRF ve diğer saldırılara karşı HTTP başlıkları

### Token Güvenliği

- Access token'lar 15 dakika geçerlidir
- Refresh token'lar 7 gün geçerlidir
- Token'lar Redis'te blacklist olarak takip edilir
- Hassas işlemler için fresh token gereksinimi
- Tüm token'lar unique JTI (JWT ID) içerir

## Testler

Testleri çalıştırmak için `pytest` kullanılabilir:

```bash
pytest
```
Testler unit, integration ve functional klasorlerine ayrilacak sekilde organize edilir. Kod kalitesi icin `pytest-cov` kullanilarak kapsama raporu alinabilir:

```bash
pytest --cov=backend --cov=frontend tests/
```

## API Dokumantasyonu

Backend API'lari OpenAPI (Swagger) standardina uygun sekilde belgelenmektedir. Calisan bir sunucu uzerinde `/api/docs` adresinden interaktif dokumanlara erisilebilir. Bu yontem frontend gelistiricileri icin net bir kontrat saglar ve API surumlerini takip etmeyi kolaylastirir.

### Analytics Uc Noktalari

Yonetim panelindeki gelismis raporlar icin eklenen API'lar:

- `/api/admin/analytics/summary` – Belirli tarihler arasinda aktif kullanici, yeni kayit, odeme ve pasif kullanici sayilarini dondurur.
- `/api/admin/analytics/plans` – Abonelik planlarina gore kullanici dagilimini listeler.
- `/api/admin/analytics/usage` – Yapilan toplam tahmin ve sistem olayi sayisini dondurur.

### Orkestrasyon (Konsensüs) API
Rejim kapısı + konsensüs ile çoklu motor çıktısını tek karara indirger.

```
POST /api/decision/score-multi
{
  "symbol": "BTCUSDT",
  "timeframe": "1h",
  "engines": ["KM1","KM2","KM3","KM4"],
  "ohlcv": [
    {"ts":"2025-08-24T12:00:00Z","open":...,"high":...,"low":...,"close":...,"volume":...}
  ],
  "params": {
    "KM1": {"ema_fast":12,"ema_slow":48},
    "KM2": {"atr_window":14}
  },
  "account_value": 100000
}
```

- `symbol` ve `timeframe` alanları zorunludur.
- `ohlcv` verisi ISO zaman damgası ve sayısal OHLCV kolonlarını içermeli, en az 50 bar barındırmalıdır.
- `engines` boş bırakılırsa kayıtlı tüm motorlar çalıştırılır; bilinmeyen motor ID'leri hata döndürür.
- `params` altındaki anahtarlar motor kimlikleriyle eşleşmelidir.

**Örnek yanıt**
```json
{
  "symbol":"BTCUSDT",
  "timeframe":"1h",
  "regime":{"label":"mixed","trend_strength":0.0012,"vol_pct":0.018},
  "consensus":{
    "label":"buy",
    "score_raw":0.32,
    "expected_return":0.046,
    "confidence":0.61,
    "conf_int":[0.01,0.08],
    "horizon_days":5.2,
    "position_fraction":0.02,
    "position_value":2000.0,
    "stop_loss":-0.032,
    "take_profit":0.078,
    "rationale":["KM1:buy(0.62)","KM2:hold(0.40)","KM3:buy(0.65)","KM4:hold(0.00)"],
    "top_drivers":["KM3","KM1","KM2"]
  },
  "engines": { "...": "tekil motor çıktıları" }
}
```

## Guvenlik Notlari

Sifreler `werkzeug` kutuphanesi ile guclu bicimde hashlenir ve JWT tabanli oturumlar kullanilir. Kullanici girislerinde olusan **refresh token** degeri `user_sessions` tablosunda saklanir ve token yenileme islemlerinde bu tablo uzerinden dogrulama yapilir. CSRF korumasi icin her istek `X-CSRF-Token` basligi ile dogrulanir. RBAC modeli ile yetki kontrolu saglanir. Flask-Limiter kullanilarak API istekleri oran sinirlariyla korunur. Hassas islemler Celery uzerinden gerceklestirilir ve kritik olaylarda `send_security_alert_task` tetiklenerek loglama yapilir.

## Dosya Açıklamaları

Bu bölümde proje deposundaki ana dosya ve klasörlerin kısa açıklamaları listelenmiştir. Uygulamanın yapısı hakkında hızlı bir bakış sağlar.

### Kök Dizin

- `wsgi.py` - Flask uygulamasını başlatan giriş noktası.
- `.env.example` ve `.env` - Ortam değişkenlerini tanımlayan örnek dosyalar.
- `.github/` - CI iş akışlarının yer aldığı klasör.
- `docker-compose.yml` - Gerekli servisleri içeren Docker bileşen tanımı.
- `scripts/` - Kurulum ve geliştirmeye yardımcı betikler.
- `backend/` - Sunucu tarafı uygulama kodları.
- `frontend/` - Statik HTML dosyaları ve istemci betikleri.
- `migrations/` - Veritabanı göç dosyaları.
- `tests/` - Pytest birim testleri.

### `backend/` Klasörü

- `__init__.py` - `create_app` fonksiyonunu içerir, uygulamayı ve uzantıları yapılandırır.
- `config.py` - Ortama özel yapılandırma sınıfları.
- `constants.py` - Abonelik planı ile ilgili sabit değerler.
- `Dockerfile` - API servisinin Docker imajı için talimatlar.
- `requirements.txt` - Backend bağımlılık listesi.
- `.env.example` - Backend için örnek ortam değişkenleri.

Alt klasörler:

* `api/`
  * `__init__.py` - API Blueprint tanımı.
  * `routes.py` - Kripto para analiz uç noktaları.
* `auth/`
  * `__init__.py` - Kimlik doğrulama Blueprint'i.
  * `jwt_utils.py` - JWT üretme ve doğrulama yardımcıları.
  * `middlewares.py` - JWT ve CSRF kontrolü yapan dekoratörler.
  * `routes.py` - Kullanıcı kayıt/giriş işlemleri.
* `admin_panel/`
  * `__init__.py` - Yönetici paneli Blueprint'i.
  * `routes.py` - Yöneticiye özel API uç noktaları.
* `db/`
  * `__init__.py` - SQLAlchemy `db` nesnesi.
  * `models.py` - Kullanıcı, oturum ve abonelik tabloları gibi veritabanı modelleri.
* `core/`
  * `__init__.py` - Boş modül dosyası.
  * `services.py` - Analiz ve tahmin işlemlerini yöneten sınıflar.
* `tasks/`
  * `__init__.py` - Celery paket tanımı.
  * `celery_tasks.py` - Arka plan görevleri ve zamanlanmış işler.
* `frontend/`
  * `__init__.py` - Basit Blueprint.
  * `routes.py` - HTML şablonlarını sunan rotalar.
* `payment/`
  * `routes.py` - Ödeme işlemleri için API uç noktaları.
* `templates/` - Sunucu taraflı render edilen Jinja2 şablonları.
* `utils/`
  * `alarms.py` - Slack/Telegram gibi yerlere uyarı gönderen yardımcılar.
  * `decorators.py` - Abonelik planı ve izin kontrolleri için dekoratörler.
  * `helpers.py` - Ortak yardımcı fonksiyonlar.
  * `rbac.py` - Rol tabanlı erişim kontrolü kurulum fonksiyonları.

### `frontend/` Klasörü

Ana klasördeki `.html` dosyaları statik sayfalardır: `index.html`, `giris.html`, `kayit.html`, `abonelik.html`, `dashboard.html`, `sifremi-unuttum.html`, `reset-password.html` ve `prediction-display.html`. Bunlar Flask tarafından servis edilen basit arayüzleri içerir.

`static/` klasöründe istemci JavaScript kodları (`api.js`) ve diğer statik varlıklar bulunur.

Ek olarak `admin/promo-codes-advanced.html` dosyası React ve Tailwind kullanılarak hazırlanmış gelişmiş promosyon kodu oluşturma formu örneğini içerir.

### Diğer Klasörler

- `migrations/` - Alembic tarafından oluşturulacak veritabanı göç dosyaları için yer tutucu.
- `tests/` - Uygulamanın temel işlevlerini doğrulayan Pytest testleri.
- `scripts/` - Ortam kurulumuna yardımcı betikler. Burada ayrıca `crypto_ta.py`
  dosyası bulunur ve çevrimdışı modda örnek teknik analiz yapar.
### Dizin Yapısı

```text
.
├── backend/
│   ├── admin_panel/
│   ├── api/
│   ├── auth/
│   ├── payment/
│   ├── core/
│   ├── db/
│   ├── frontend/
│   ├── tasks/
│   ├── templates/
│   ├── utils/
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── abonelik.html
│   ├── abonelik2.html
│   ├── dashboard.html
│   ├── prediction-display.html
│   ├── frontend-crypto-analysis-dashboard
│   ├── giris.html
│   ├── homepage-unregistered.html
│   ├── kayit.html
│   ├── reset-password.html
│   ├── sifremi-unuttum.html
│   ├── ytdcrypto-admin-dashboard
│   └── static/
├── migrations/
├── scripts/
├── tests/
├── wsgi.py
├── docker-compose.yml
├── README.md
├── LICENSE
├── .env.example
└── .env
```

## Katkı Rehberi

Projeye katkıda bulunmak isterseniz aşağıdaki adımları takip edebilirsiniz:

1. Depoyu çatallayın ve kendi hesabınıza kopyalayın.
2. Geliştirme için yeni bir dal (`git checkout -b özellik-adi`) oluşturun.
3. Yaptığınız değişiklikleri açık ve anlamlı commit mesajlarıyla kaydedin.
4. Değişikliklerinizi GitHub üzerinde bir **Pull Request** olarak gönderin.

Katkılarınız her zaman memnuniyetle karşılanır. Sorularınız için yeni bir konu
açabilir veya mevcut tartışmalara katılabilirsiniz.

## Lisans

Bu proje MIT lisansı altında sunulmaktadır. Ayrıntılar için `LICENSE` dosyasına
bakabilirsiniz.


## Secrets & ENV Yönetimi

Üretim ortamında tüm hassas bilgiler GitHub Actions Secrets üzerinden
yönetilir. Yerel geliştirmede gerekli değerler `.env` dosyalarına yazılır; bu
dosyalar depoya eklenmez ve `.gitignore` tarafından korunur. Örnek
konfigürasyonlar için `*.env.example` dosyalarına bakabilirsiniz.


