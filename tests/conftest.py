# Test ortamı için güvenli varsayılanlar (CI ve lokal)
import os

# İzole ve yan etkisiz bir test DB'si
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("FLASK_ENV", "testing")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

# Burada bilerek herhangi bir app fixture'ı oluşturmadık;
# projedeki testler backend.create_app vb. kendi akışını çağırıyorsa
# bu env değişkenleri yeterli olur. İleride ihtiyaç olursa
# app fixture'ı ekleyebiliriz.
