"""Add security enhancements

Revision ID: security_001
Revises: remove_subscription_plan_limits
Create Date: 2025-01-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'security_001'
down_revision = 'remove_subscription_plan_limits'
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')))

    with op.batch_alter_table('user_sessions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('jti', sa.String(length=64), nullable=False, unique=True))
        batch_op.add_column(sa.Column('last_used', sa.DateTime(), nullable=True, server_default=sa.func.now()))
        batch_op.add_column(sa.Column('user_agent', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('ip_address', sa.String(length=45), nullable=True))
        batch_op.add_column(sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')))
        batch_op.create_index('ix_user_sessions_jti', ['jti'], unique=True)

    op.create_table(
        'token_blacklist',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('jti', sa.String(length=64), nullable=False),
        sa.Column('token_type', sa.String(length=20), nullable=False),
        sa.Column('blacklisted_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('reason', sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('jti')
    )
    op.create_index('ix_token_blacklist_jti', 'token_blacklist', ['jti'], unique=True)
    op.create_index('ix_token_blacklist_expires_at', 'token_blacklist', ['expires_at'])

    op.create_table(
        'security_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_security_events_user_id', 'security_events', ['user_id'])
    op.create_index('ix_security_events_event_type', 'security_events', ['event_type'])
    op.create_index('ix_security_events_timestamp', 'security_events', ['timestamp'])
    op.create_index('ix_security_events_ip_address', 'security_events', ['ip_address'])


def downgrade():
    op.drop_index('ix_security_events_ip_address', table_name='security_events')
    op.drop_index('ix_security_events_timestamp', table_name='security_events')
    op.drop_index('ix_security_events_event_type', table_name='security_events')
    op.drop_index('ix_security_events_user_id', table_name='security_events')
    op.drop_table('security_events')

    op.drop_index('ix_token_blacklist_expires_at', table_name='token_blacklist')
    op.drop_index('ix_token_blacklist_jti', table_name='token_blacklist')
    op.drop_table('token_blacklist')

    with op.batch_alter_table('user_sessions', schema=None) as batch_op:
        batch_op.drop_index('ix_user_sessions_jti')
        batch_op.drop_column('is_active')
        batch_op.drop_column('ip_address')
        batch_op.drop_column('user_agent')
        batch_op.drop_column('last_used')
        batch_op.drop_column('jti')

    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('is_active')
