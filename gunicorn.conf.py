# Güvenlik odaklı basit gunicorn konfigürasyonu
import multiprocessing

bind = "0.0.0.0:8000"
workers = max(2, multiprocessing.cpu_count())
threads = 2
timeout = 120
graceful_timeout = 30

# İstek satırı ve header alanı sınırları (çok büyük header/line ile gelen saldırılara karşı)
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# TMP alanı (çok büyük body'leri disk yerine RAM'e yazma riskini azalt)
worker_tmp_dir = "/tmp"

# Loglar
accesslog = "-"
errorlog = "-"
loglevel = "info"

