"""Secure database query functions with proper parameterization."""

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, or_, text
from sqlalchemy.exc import SQLAlchemyError

from .models import User, db

logger = logging.getLogger(__name__)


class SecureQueryManager:
    """Secure query manager with parameterization and logging."""

    @staticmethod
    def get_user_by_email(email: str) -> Optional[User]:
        """Securely get user by email."""
        try:
            return db.session.query(User).filter(User.email == email).first()
        except SQLAlchemyError as exc:  # pragma: no cover - defensive
            logger.error("Database error in get_user_by_email: %s", exc)
            return None

    @staticmethod
    def get_user_by_id(user_id: int) -> Optional[User]:
        """Securely get user by ID."""
        try:
            return db.session.query(User).filter(User.id == user_id).first()
        except SQLAlchemyError as exc:  # pragma: no cover - defensive
            logger.error("Database error in get_user_by_id: %s", exc)
            return None

    @staticmethod
    def search_users_secure(
        search_term: str, limit: int = 50, offset: int = 0
    ) -> List[User]:
        """Secure user search with parameterized LIKE query."""
        try:
            search_term = search_term.strip()
            if not search_term or len(search_term) > 100:
                return []

            pattern = f"%{search_term}%"
            return (
                db.session.query(User)
                .filter(
                    or_(
                        User.username.ilike(pattern),
                        User.email.ilike(pattern),
                        User.full_name.ilike(pattern),
                    )
                )
                .limit(limit)
                .offset(offset)
                .all()
            )
        except SQLAlchemyError as exc:  # pragma: no cover - defensive
            logger.error("Database error in search_users_secure: %s", exc)
            return []

    @staticmethod
    def get_user_analytics_secure(
        start_date: str, end_date: str, user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Secure analytics query with parameterized statements."""
        try:
            query = db.session.query(User).filter(
                and_(User.created_at >= start_date, User.created_at <= end_date)
            )
            if user_id:
                query = query.filter(User.id == user_id)

            total_users = query.count()
            active_users = query.filter(User.is_active.is_(True)).count()
            return {
                "total_users": total_users,
                "active_users": active_users,
                "inactive_users": total_users - active_users,
            }
        except SQLAlchemyError as exc:  # pragma: no cover - defensive
            logger.error("Database error in get_user_analytics_secure: %s", exc)
            return {"error": "Analytics query failed"}

    @staticmethod
    def execute_raw_query_secure(
        query: str, params: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Execute raw SQL query with basic keyword validation and parameters."""
        try:
            dangerous_keywords = {
                "drop",
                "delete",
                "truncate",
                "alter",
                "create",
                "insert",
                "update",
                "grant",
                "revoke",
            }
            lower_query = query.lower().strip()
            if any(keyword in lower_query for keyword in dangerous_keywords):
                logger.warning(
                    "Dangerous SQL keyword detected in query: %s", lower_query
                )
                raise ValueError("Query contains dangerous keyword")

            return db.session.execute(text(query), params or {}).fetchall()
        except (SQLAlchemyError, ValueError) as exc:
            logger.error("Database error in execute_raw_query_secure: %s", exc)
            raise
