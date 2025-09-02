from flask import jsonify
from sqlalchemy.exc import SQLAlchemyError


def register_error_handlers(app):
    """Global hata yakalama"""

    @app.errorhandler(500)
    def internal_error(error):
        from ..models.db import db

        db.session.rollback()
        return jsonify({"error": "Internal Server Error"}), 500

    @app.errorhandler(SQLAlchemyError)
    def handle_db_error(error):
        from ..models.db import db

        db.session.rollback()
        return jsonify({"error": "Database Error"}), 500
