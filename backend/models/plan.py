import json
from datetime import datetime
from backend.db import db

class Plan(db.Model):
    __tablename__ = 'plans'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    price = db.Column(db.Float, nullable=False)
    features = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def features_dict(self):
        try:
            return json.loads(self.features) if self.features else {}
        except Exception:
            return {}

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "price": self.price,
            "features": self.features_dict(),
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
        }
