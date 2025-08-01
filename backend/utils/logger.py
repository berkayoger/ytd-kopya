from __future__ import annotations

def create_log(
    user_id: str,
    username: str,
    ip_address: str,
    action: str,
    target: str = "",
    description: str = "",
    status: str = "success",
    source: str = "web",
    user_agent: str = ""
):
    """Persist a simple application log entry."""
    from backend import db
    from backend.models.log import Log
    from uuid import uuid4
    import datetime

    log = Log(
        id=str(uuid4()),
        timestamp=datetime.datetime.utcnow(),
        user_id=user_id,
        username=username,
        ip_address=ip_address,
        action=action,
        target=target,
        description=description,
        status=status,
        source=source,
        user_agent=user_agent,
    )
    db.session.add(log)
    db.session.commit()
    return log
