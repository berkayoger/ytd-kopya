from __future__ import annotations

from datetime import datetime

from backend.db import db


class APIKey(db.Model):
    __tablename__ = "api_keys"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    key_hash = db.Column(db.LargeBinary, nullable=False)
    rate_limit_override = db.Column(db.String(50))
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    expires_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_used_at = db.Column(db.DateTime)
    usage_count = db.Column(db.Integer, default=0, nullable=False)

    user = db.relationship("User", backref=db.backref("api_keys", lazy=True))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "is_active": self.is_active,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_used_at": (
                self.last_used_at.isoformat() if self.last_used_at else None
            ),
            "usage_count": self.usage_count,
            "rate_limit_override": self.rate_limit_override,
        }
