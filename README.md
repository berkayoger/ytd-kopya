# YTD-Kopya

YTD-Kopya, kripto ve borsa verileri üzerinde teknik analiz, tahmin ve plan/limit yönetimi sağlayan bir platformdur. Flask tabanlı backend ile React ve TailwindCSS destekli arayüz sunar. Sistem Redis ve TimescaleDB ile gerçek zamanlı verileri işler, Prophet ile fiyat tahmini üretir.

## Özellikler

- Gerçek zamanlı fiyat ve hacim takibi
- RSI, MACD gibi teknik göstergelerin yorumlanması
- Prophet tabanlı tahmin motoru
- Kullanıcı planı ve limit kontrolleri
- Özellik bayraklarıyla kademeli dağıtım
- Mobil uyumlu arayüz (React + TailwindCSS)
- GitHub Actions ile CI/CD

## Teknoloji Yığını

- Flask & FastAPI
- SQLAlchemy & TimescaleDB
- Redis
- React & TailwindCSS
- Prophet
- GitHub Actions

## Kurulum

1. Depoyu klonlayın:
   ```bash
   git clone <repo-url>
   ```
2. Ortam değişkenlerini `.env.example` dosyasından kopyalayın.
3. Bağımlılıkları yükleyin:
   ```bash
   pip install -r requirements.txt
   ```
4. Veritabanı migrasyonlarını uygulayın:
   ```bash
   flask db upgrade
   ```
5. Uygulamayı çalıştırın:
   ```bash
   flask run
   ```

## Testler

```bash
pytest
```

## Katkı

Pull request açmadan önce testleri çalıştırın ve açıklayıcı commit mesajları kullanın.

## Lisans

Bu proje MIT Lisansı altındadır. Ayrıntılar için `LICENSE` dosyasına bakın.
