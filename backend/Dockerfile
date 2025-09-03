FROM python:3.12-slim AS builder
WORKDIR /app
ENV PIP_NO_CACHE_DIR=1
# Hem kök hem backend gereksinimleri için wheel oluştur
COPY requirements.txt /tmp/req.root.txt
COPY backend/requirements.txt /tmp/req.backend.txt
RUN python -m pip install --upgrade pip \
 && pip wheel -w /wheels -r /tmp/req.root.txt \
 && pip wheel -w /wheels -r /tmp/req.backend.txt
COPY . .

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends tini && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY --from=builder /wheels /wheels
RUN pip install --no-cache /wheels/* && rm -rf /wheels
COPY . .
RUN useradd -m app && chown -R app:app /app
USER app
ENTRYPOINT ["/usr/bin/tini","--"]
CMD ["gunicorn","-c","/app/gunicorn.conf.py","wsgi:app"]
