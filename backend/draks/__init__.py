from flask import Blueprint

# /api/draks altında karar motoru uçları
draks_bp = Blueprint("draks", __name__, url_prefix="/api/draks")

# Rotaları yükle
from . import routes  # noqa: E402,F401
