from datetime import datetime

from sqlalchemy import Column, DateTime, String

from backend.db import db


class Log(db.Model):
    """Stores application log entries"""

    __tablename__ = "logs"

    id = Column(String, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    user_id = Column(String)
    username = Column(String)
    ip_address = Column(String)
    action = Column(String)
    target = Column(String)
    description = Column(String)
    status = Column(String)
    source = Column(String)
    user_agent = Column(String)

    def to_dict(self) -> dict:
        """Serialize model to dictionary"""

        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id,
            "username": self.username,
            "ip_address": self.ip_address,
            "action": self.action,
            "target": self.target,
            "description": self.description,
            "status": self.status,
            "source": self.source,
            "user_agent": self.user_agent,
        }
