FROM python:3.12-slim

# Ortam ayarları: cache kapalı, güvenli I/O
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# hadolint DL3008: apt paket sürümleri pinlenmeli
# Sürüm, temel imaja bağlı olarak değişebileceğinden ARG ile pinliyoruz
ARG TINI_VERSION=0.19.0-1
RUN apt-get update \
 && apt-get install -y --no-install-recommends tini=${TINI_VERSION} \
 && rm -rf /var/lib/apt/lists/*

# hadolint DL3013, DL3042: pip kurulumunda sürümler requirements dosyalarından
# ve cache kullanılmıyor
COPY requirements.txt backend/requirements.txt ./
RUN python -m pip install --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt -r backend/requirements.txt

COPY . .
RUN useradd -m app && chown -R app:app /app
USER app
ENTRYPOINT ["/usr/bin/tini","--"]
CMD ["gunicorn","-c","/app/gunicorn.conf.py","wsgi:app"]
