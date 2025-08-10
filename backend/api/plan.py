*** Yeni dosya: backend/api/plan.py ***
+"""
+Plan API blueprint proxy dosyası.
+Eski import yollarının bozulmaması için bu dosya eklenmiştir.
+"""
+
+try:
+    # Eğer plan bir klasör ve routes.py içinde tanımlıysa
+    from backend.api.plan.routes import plan_bp
+except ModuleNotFoundError:
+    # Eğer plan doğrudan __init__.py içinde tanımlıysa
+    from backend.api.plan import plan_bp
+
+__all__ = ["plan_bp"]
