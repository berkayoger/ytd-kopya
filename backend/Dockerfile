FROM python:3.11-slim
WORKDIR /app

# Install dependencies
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
# CI’da sürpriz çıkmasın diye açıkça ekle
RUN pip install --no-cache-dir PyYAML

# Copy backend and frontend code
COPY backend ./backend
COPY frontend ./frontend
COPY wsgi.py ./wsgi.py

# Varsayılan servis portu
EXPOSE 5000
# Konteyner içinden dışarıya dinleme adresi/portu
ENV HOST=0.0.0.0
ENV PORT=5000

# Giriş noktası: wsgi.py (socketio.run host/port'u env'den okur)
CMD ["python", "wsgi.py"]
