from flask import request
from backend.db import db
from backend.db.models import AuditLog


def log_action(user=None, action: str = "", details=None) -> None:
    """Record an audit log entry for the given user action."""
    log = AuditLog(
        user_id=getattr(user, "id", None),
        username=getattr(user, "email", None) or getattr(user, "username", None),
        action=action,
        ip_address=request.remote_addr if request else None,
        details=details,
    )
    db.session.add(log)
    db.session.commit()
