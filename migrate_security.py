from sqlalchemy import text

from backend import create_app
from backend.db import db

app = create_app()
with app.app_context():
    # Users tablosuna is_active kolonu ekle
    try:
        with db.engine.connect() as conn:
            conn.execute(
                text("ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT 1")
            )
            conn.commit()
        print("✓ users.is_active kolonu eklendi")
    except Exception as e:
        print(f"users.is_active: {e}")

    # user_sessions tablosuna yeni kolonlar
    try:
        with db.engine.connect() as conn:
            conn.execute(
                text("ALTER TABLE user_sessions ADD COLUMN jti VARCHAR(64) UNIQUE")
            )
            conn.execute(
                text("ALTER TABLE user_sessions ADD COLUMN last_used DATETIME")
            )
            conn.execute(text("ALTER TABLE user_sessions ADD COLUMN user_agent TEXT"))
            conn.execute(
                text("ALTER TABLE user_sessions ADD COLUMN ip_address VARCHAR(45)")
            )
            conn.execute(
                text("ALTER TABLE user_sessions ADD COLUMN is_active BOOLEAN DEFAULT 1")
            )
            conn.commit()
        print("✓ user_sessions kolonları eklendi")
    except Exception as e:
        print(f"user_sessions: {e}")

    # token_blacklist tablosunu oluştur
    try:
        with db.engine.connect() as conn:
            conn.execute(
                text(
                    """
            CREATE TABLE IF NOT EXISTS token_blacklist (
                id INTEGER PRIMARY KEY,
                jti VARCHAR(64) NOT NULL UNIQUE,
                token_type VARCHAR(20) NOT NULL,
                blacklisted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                expires_at DATETIME,
                reason VARCHAR(255)
            )
            """
                )
            )
            conn.commit()
        print("✓ token_blacklist tablosu oluşturuldu")
    except Exception as e:
        print(f"token_blacklist: {e}")

    # security_events tablosunu oluştur
    try:
        with db.engine.connect() as conn:
            conn.execute(
                text(
                    """
            CREATE TABLE IF NOT EXISTS security_events (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                event_type VARCHAR(50) NOT NULL,
                ip_address VARCHAR(45),
                user_agent TEXT,
                success BOOLEAN DEFAULT 1,
                details TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
            """
                )
            )
            conn.commit()
        print("✓ security_events tablosu oluşturuldu")
    except Exception as e:
        print(f"security_events: {e}")

    print("Database güvenlik tabloları başarıyla oluşturuldu!")
