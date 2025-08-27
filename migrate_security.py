from backend import create_app
from backend.db import db
from flask_migrate import upgrade

app = create_app()
with app.app_context():
    db.create_all()
    print("Database tables created successfully")
