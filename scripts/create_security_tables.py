#!/usr/bin/env python3
import os
import sys
from sqlalchemy import create_engine, text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _ddl_for_dialect(dialect: str):
    if dialect == "sqlite":
        return [
            """
            CREATE TABLE IF NOT EXISTS audit_logs (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                action TEXT NOT NULL,
                resource_type TEXT,
                resource_id TEXT,
                ip_address TEXT,
                user_agent TEXT,
                request_path TEXT,
                request_method TEXT,
                status_code INTEGER,
                response_time_ms INTEGER,
                details TEXT,
                error_message TEXT,
                created_at TEXT,
                updated_at TEXT
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS rate_limits (
                id TEXT PRIMARY KEY,
                identifier TEXT NOT NULL,
                identifier_type TEXT NOT NULL,
                endpoint TEXT,
                requests_made INTEGER DEFAULT 1 NOT NULL,
                limit_per_window INTEGER NOT NULL,
                window_start TEXT,
                window_duration_seconds INTEGER DEFAULT 3600 NOT NULL,
                is_blocked INTEGER DEFAULT 0 NOT NULL,
                blocked_until TEXT,
                created_at TEXT,
                updated_at TEXT
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS system_settings (
                id TEXT PRIMARY KEY,
                key TEXT UNIQUE NOT NULL,
                value TEXT,
                value_type TEXT DEFAULT 'string' NOT NULL,
                description TEXT,
                is_sensitive INTEGER DEFAULT 0 NOT NULL,
                is_readonly INTEGER DEFAULT 0 NOT NULL,
                category TEXT,
                created_at TEXT,
                updated_at TEXT
            );
            """,
        ], [
            "CREATE INDEX IF NOT EXISTS ix_audit_logs_created_action ON audit_logs(created_at, action);",
            "CREATE INDEX IF NOT EXISTS ix_rate_limits_identifier_type ON rate_limits(identifier, identifier_type);",
        ]

    # Default to Postgres-compatible DDL
    return [
        """
        CREATE EXTENSION IF NOT EXISTS pgcrypto;
        """,
        """
        CREATE TABLE IF NOT EXISTS audit_logs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID,
            action VARCHAR(50) NOT NULL,
            resource_type VARCHAR(50),
            resource_id VARCHAR(255),
            ip_address VARCHAR(45),
            user_agent TEXT,
            request_path VARCHAR(500),
            request_method VARCHAR(10),
            status_code INTEGER,
            response_time_ms INTEGER,
            details JSONB,
            error_message TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
            updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS rate_limits (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            identifier VARCHAR(255) NOT NULL,
            identifier_type VARCHAR(20) NOT NULL,
            endpoint VARCHAR(200),
            requests_made INTEGER DEFAULT 1 NOT NULL,
            limit_per_window INTEGER NOT NULL,
            window_start TIMESTAMPTZ DEFAULT NOW() NOT NULL,
            window_duration_seconds INTEGER DEFAULT 3600 NOT NULL,
            is_blocked BOOLEAN DEFAULT FALSE NOT NULL,
            blocked_until TIMESTAMPTZ,
            created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
            updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS system_settings (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            key VARCHAR(100) UNIQUE NOT NULL,
            value TEXT,
            value_type VARCHAR(20) DEFAULT 'string' NOT NULL,
            description TEXT,
            is_sensitive BOOLEAN DEFAULT FALSE NOT NULL,
            is_readonly BOOLEAN DEFAULT FALSE NOT NULL,
            category VARCHAR(50),
            created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
            updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
        );
        """,
    ], [
        "CREATE INDEX IF NOT EXISTS ix_audit_logs_created_action ON audit_logs(created_at, action);",
        "CREATE INDEX IF NOT EXISTS ix_audit_logs_user_action ON audit_logs(user_id, action);",
        "CREATE INDEX IF NOT EXISTS ix_rate_limits_identifier_type ON rate_limits(identifier, identifier_type);",
    ]


def create_security_tables():
    database_url = os.getenv("DATABASE_URL") or os.getenv("SQLALCHEMY_DATABASE_URI")
    if not database_url:
        print("Error: DATABASE_URL or SQLALCHEMY_DATABASE_URI required")
        return

    engine = create_engine(database_url)
    dialect = engine.dialect.name
    ddls, indexes = _ddl_for_dialect(dialect)

    with engine.connect() as conn:
        for stmt in ddls:
            try:
                conn.execute(text(stmt))
                conn.commit()
                logger.info("Applied DDL statement")
            except Exception as e:
                logger.error(f"DDL failed: {e}")
        for idx in indexes:
            try:
                conn.execute(text(idx))
                conn.commit()
                logger.info("Applied index statement")
            except Exception as e:
                logger.warning(f"Index apply failed: {e}")

    logger.info("Security tables setup completed")


if __name__ == "__main__":
    create_security_tables()

