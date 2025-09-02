# backend/api/__init__.py

from flask import Blueprint

# API blueprint; routes are registered explicitly in create_app.
api_bp = Blueprint("api", __name__)
