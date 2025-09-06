from __future__ import annotations

from flask import Blueprint
from flask_restx import Api, Namespace, Resource


def create_v1_blueprint(
    base_url: str = "/api/v1", title: str = "YTD-Kopya API", version: str = "1.0.0"
) -> tuple[Blueprint, Api]:
    """Create a RESTX-powered API v1 blueprint with minimal health/doc routes."""
    bp = Blueprint("api_v1", __name__, url_prefix=base_url)
    api = Api(
        bp,
        version=version,
        title=title,
        description="Cryptocurrency Analysis API",
        doc="/docs",  # Swagger UI at /api/v1/docs
    )

    ns_health = Namespace("health", path="/health", description="Health checks")

    @ns_health.route("")
    class Health(Resource):
        def get(self):  # noqa: D401
            return {"status": "healthy", "service": "ytd-kopya-api"}, 200

    api.add_namespace(ns_health)
    return bp, api

