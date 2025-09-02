from flask import Blueprint, jsonify, request

from .security import generate_csrf_token

bp = Blueprint("csrf_api", __name__)


@bp.get("/token")
def get_csrf_token():
    """
    Cookie-session kullanan istemciler için basit bir CSRF token üreticisi.
    Beklenen: client tarafında bir 'session_id' (ör. login sonrası atanmış) cookie ya da header.
    Bearer-token saf API akışlarında kullanımı zorunlu değildir.
    """
    sid = request.cookies.get("sid") or request.headers.get("X-Session-Id")
    if not sid:
        return jsonify({"detail": "missing session id"}), 422
    try:
        token = generate_csrf_token(sid)
    except Exception:
        return jsonify({"detail": "csrf not configured"}), 500
    return jsonify({"csrf": token}), 200
