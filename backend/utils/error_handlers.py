"""Enhanced error handling utilities for YTD-Kopya"""

from flask import jsonify, g
from werkzeug.exceptions import HTTPException
import logging

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Base application error with structured response"""
    status_code = 500
    code = "internal_error"

    def __init__(self, message: str, status_code: int | None = None, code: str | None = None, details=None):
        super().__init__(message)
        if status_code is not None:
            self.status_code = status_code
        if code is not None:
            self.code = code
        self.details = details
        self.message = message


class BadRequest(AppError):
    """400 Bad Request"""
    status_code = 400
    code = "bad_request"


class Unauthorized(AppError):
    """401 Unauthorized"""
    status_code = 401
    code = "unauthorized"


class Forbidden(AppError):
    """403 Forbidden"""
    status_code = 403
    code = "forbidden"


class NotFound(AppError):
    """404 Not Found"""
    status_code = 404
    code = "not_found"


class Conflict(AppError):
    """409 Conflict"""
    status_code = 409
    code = "conflict"


class RateLimitExceeded(AppError):
    """429 Rate Limit Exceeded"""
    status_code = 429
    code = "rate_limit_exceeded"


def _make_error_response(err: AppError, status: int):
    """Create standardized error response"""
    return {
        "error": {
            "code": err.code,
            "message": err.message,
            "details": err.details,
        },
        "meta": {
            "request_id": getattr(g, "request_id", None)
        }
    }, status


def register_enhanced_error_handlers(app):
    """Register enhanced error handlers that work with existing system"""
    
    @app.errorhandler(AppError)
    def handle_app_error(err: AppError):
        logger.error(f"Application error: {err.message}", extra={"error_code": err.code})
        return jsonify(_make_error_response(err, err.status_code)[0]), err.status_code

    @app.errorhandler(HTTPException)
    def handle_http_exception(err: HTTPException):
        app_err = AppError(err.description or err.name, status_code=err.code, code="http_error")
        return jsonify(_make_error_response(app_err, err.code)[0]), err.code

    @app.errorhandler(Exception)
    def handle_unexpected(err: Exception):
        logger.exception("Unhandled exception")
        app_err = AppError("Internal Server Error")
        return jsonify(_make_error_response(app_err, 500)[0]), 500


def register_error_handlers(app):
    """
    Alias for backward compatibility with existing code.
    This allows existing register_error_handlers calls to work.
    """
    register_enhanced_error_handlers(app)