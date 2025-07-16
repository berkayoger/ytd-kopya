from datetime import datetime
import logging

from flask import current_app

from backend import celery_app, create_app, db
from backend.db.models import User, UserRole
from backend.models.plan import Plan

logger = logging.getLogger(__name__)


@celery_app.task
def auto_downgrade_expired_plans():
    """Downgrade users whose plan has expired to the Free plan."""
    logger.info("Checking for expired plans to downgrade")
    ctx_app = current_app._get_current_object() if current_app else create_app()
    with ctx_app.app_context():
        now = datetime.utcnow()
        free_plan = Plan.query.filter_by(name="Free").first()
        if not free_plan:
            logger.warning("Free plan not found; skipping downgrade")
            return
        users = (
            User.query.filter(
                User.plan_expire_at != None,
                User.plan_expire_at < now,
                User.plan_id != free_plan.id,
                User.role == UserRole.USER,
            ).all()
        )
        for u in users:
            old_plan = u.plan_id
            u.plan_id = free_plan.id
            u.plan_expire_at = None
            db.session.commit()
            logger.info("Downgraded user %s from %s", u.username, old_plan)


@celery_app.task
def auto_expire_boosts():
    """Clear boost features for users where the boost period expired."""
    logger.info("Checking for expired boosts")
    ctx_app = current_app._get_current_object() if current_app else create_app()
    with ctx_app.app_context():
        now = datetime.utcnow()
        users = User.query.filter(
            User.boost_expire_at != None,
            User.boost_expire_at < now,
        ).all()
        for u in users:
            u.boost_features = None
            u.boost_expire_at = None
            db.session.commit()
            logger.info("Expired boost cleared for user %s", u.username)
