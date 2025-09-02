"""Plan API blueprint proxy.

Eski import yolu `from backend.api.plan import plan_bp` olan yerler için
gerçek blueprint'i `plan_routes` modülünden dışa aktarır.
"""

# Projedeki gerçek blueprint `backend/api/plan_routes.py` içinde tanımlı.
# Konum değişikliğinde tek noktadan yönlendirme yapabilmek için proxy kullanılır.
from backend.api.plan_routes import plan_bp  # noqa: F401

__all__ = ["plan_bp"]
