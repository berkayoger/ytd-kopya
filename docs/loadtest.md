# Yük Testi Rehberi

## HTTP + WS Senaryoları

- `locust -f tests/load/locustfile.py --headless -u 500 -r 50`
  - 500 eşzamanlı kullanıcı
  - 50 kullanıcı/s hızında artış
- WebSocket testleri için `WSUser` sınıfı kullanılabilir.

## İzleme
- Prometheus metrikleri
- Grafana dashboard’ları
- Redis queue latency
- Worker CPU/RAM

## Hedefler
- Ortalama latency < 500ms
- %95 latency < 1s
- <1% hata oranı
