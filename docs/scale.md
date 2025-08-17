# Ölçeklenebilirlik (Binlerce Kullanıcı)

## Mimarinin Özeti

```
        Users (HTTP/WebSocket)
               |
          Ingress/Nginx
               |
          Service (backend)
               |
     +---------+----------+
     |                    |
 Flask App (API/WS)   Celery Workers  <----+
     |                    |                |
     |              Redis (Broker/Cache) --+
     |                    |
 Postgres (RDS/GKE SQL)   |
                          |
                  Prometheus/Grafana
```

## Dağıtım

```bash
kubectl apply -f deploy/k8s/namespace.yaml
kubectl apply -f deploy/k8s/configmap-backend.yaml
kubectl apply -f deploy/k8s/secret-backend.yaml
kubectl apply -f deploy/k8s/service-backend.yaml
kubectl apply -f deploy/k8s/deployment-backend.yaml
kubectl apply -f deploy/k8s/hpa-backend.yaml
kubectl apply -f deploy/k8s/deployment-celery-worker.yaml
kubectl apply -f deploy/k8s/deployment-celery-beat.yaml
kubectl apply -f deploy/k8s/ingress.yaml
```

## Öneriler
- **Redis Cluster** veya managed Redis (ElastiCache/Memorystore)
- **DB read-replica** ve tablo partisyonları
- WebSocket için **Redis message_queue** kullanımı aktiftir
- HPA: CPU’ye ek olarak istek sayısı/queue uzunluğu metriklerini bağlayın
- Prometheus uyarıları: job süre p95, hata oranı, cache miss oranı
