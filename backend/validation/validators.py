"""Custom validation functions and decorators."""

import html
import logging
import re
from functools import wraps
from typing import Any, Callable, Type

import bleach
from flask import jsonify, request
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)


def validate_json(schema_class: Type[BaseModel]) -> Callable:
    """Decorator validating JSON request data with a Pydantic schema."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def decorated_function(*args: Any, **kwargs: Any):
            try:
                json_data = request.get_json(force=True)
                if not json_data:
                    return (
                        jsonify(
                            {
                                "error": "Invalid JSON data",
                                "message": "Request must contain valid JSON",
                            }
                        ),
                        400,
                    )

                validated_data = schema_class(**json_data)
                kwargs["validated_data"] = validated_data
                return func(*args, **kwargs)
            except ValidationError as exc:
                logger.warning("Validation error: %s", exc.errors())
                return (
                    jsonify({"error": "Validation failed", "details": exc.errors()}),
                    400,
                )
            except Exception as exc:  # pragma: no cover - defensive
                logger.error("Validation decorator error: %s", exc)
                return (
                    jsonify(
                        {
                            "error": "Invalid request format",
                            "message": "Request data format is invalid",
                        }
                    ),
                    400,
                )

        return decorated_function

    return decorator


def sanitize_html_input(text: str) -> str:
    """Sanitize HTML input to prevent XSS."""
    if not text:
        return ""

    text = html.escape(text)
    allowed_tags = ["b", "i", "em", "strong", "p", "br"]
    allowed_attributes: dict[str, Any] = {}
    return bleach.clean(
        text, tags=allowed_tags, attributes=allowed_attributes, strip=True
    )


def validate_sql_injection_patterns(query_string: str) -> bool:
    """Check for common SQL injection patterns in a query string."""
    suspicious_patterns = [
        r"(\bor\b|\band\b)\s+\w*\s*=\s*\w*",
        r"union\s+select",
        r"drop\s+table",
        r"delete\s+from",
        r"insert\s+into",
        r"update\s+\w+\s+set",
        r"exec\s*\(",
        r"script\s*>",
        r"javascript\s*:",
        r"--\s*$",
        r"/\*.*\*/",
        r"char\s*\(",
        r"cast\s*\(",
        r"convert\s*\(",
    ]

    query_lower = query_string.lower()
    for pattern in suspicious_patterns:
        if re.search(pattern, query_lower, re.IGNORECASE):
            return False
    return True
