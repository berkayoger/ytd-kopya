"""Admin test çalıştırma kayıt modeli."""

from datetime import datetime

from backend.db import db


class AdminTestRun(db.Model):
    __tablename__ = "admin_test_runs"

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    user_id = db.Column(db.String, nullable=True)
    username = db.Column(db.String, nullable=True)
    suite = db.Column(db.String, nullable=False)
    exit_code = db.Column(db.Integer, nullable=False)
    summary_raw = db.Column(db.Text, nullable=True)

    def to_dict(self) -> dict:
        """Serileştirme yardımcı fonksiyonu."""
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat(),
            "user_id": self.user_id,
            "username": self.username,
            "suite": self.suite,
            "exit_code": self.exit_code,
            "summary_raw": self.summary_raw,
        }

