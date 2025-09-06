import os
import subprocess
from importlib import import_module

import click
from flask.cli import with_appcontext

os.environ.setdefault("PYTHONPATH", ".")

# Resolve Flask app
flask_app_str = os.getenv("FLASK_APP_FACTORY", "backend:create_app")
mod_name, _, obj_name = flask_app_str.partition(":")
mod = import_module(mod_name)
app = (
    getattr(mod, obj_name)()
    if (obj_name and hasattr(mod, obj_name) and callable(getattr(mod, obj_name)))
    else getattr(mod, obj_name or "app")
)

db = None
try:
    if hasattr(mod, "db"):
        db = getattr(mod, "db")
    elif os.getenv("FLASK_DB_MOD"):
        db = import_module(os.getenv("FLASK_DB_MOD")).db
except Exception:
    db = None

try:
    if db:
        from flask_migrate import Migrate

        Migrate(app, db)
except Exception:
    pass


@click.group()
def cli():
    """YTD-Kopya management commands"""
    pass


@cli.command()
@click.option("--port", default=int(os.getenv("CELERY_FLOWER_PORT", 5555)), help="Flower port")
def flower(port: int):
    """Start Celery Flower monitoring dashboard."""
    subprocess.run([
        "celery",
        "-A",
        "backend.tasks.celery_tasks",
        "flower",
        f"--port={port}",
    ])


@cli.command()
@click.option("--loglevel", default=os.getenv("CELERY_LOGLEVEL", "INFO"))
@click.option("--concurrency", default=int(os.getenv("CELERY_CONCURRENCY", 4)))
def worker(loglevel: str, concurrency: int):
    """Start Celery worker."""
    subprocess.run([
        "celery",
        "-A",
        "backend.tasks.celery_tasks",
        "worker",
        f"--loglevel={loglevel}",
        f"--concurrency={concurrency}",
        "--pool=prefork",
    ])


@cli.command("dlq-status")
@with_appcontext
def dlq_status():
    from backend.tasks.celery_tasks import get_dlq_size

    click.echo(f"DLQ size: {get_dlq_size()} items")


@cli.command("dlq-requeue")
@with_appcontext
def dlq_requeue():
    from backend.tasks.celery_tasks import requeue_dlq_item

    ok = requeue_dlq_item()
    click.echo("Successfully requeued one item from DLQ" if ok else "No item requeued")


@cli.command("dlq-requeue-all")
@with_appcontext
def dlq_requeue_all():
    """Requeue all items from Dead Letter Queue"""
    from backend.tasks.celery_tasks import requeue_dlq_item, get_dlq_size
    
    initial_size = get_dlq_size()
    requeued_count = 0
    
    while get_dlq_size() > 0:
        if requeue_dlq_item():
            requeued_count += 1
        else:
            break
    
    click.echo(f"Requeued {requeued_count} items out of {initial_size} from DLQ")


@cli.command("cache-stats")
@with_appcontext
def cache_stats():
    """Show cache statistics"""
    from backend.utils.cache import _l1_cache
    
    click.echo("Cache Statistics:")
    click.echo(f"L1 Cache size: {len(_l1_cache)} / {_l1_cache.maxsize}")
    click.echo(f"L1 Cache TTL: {_l1_cache.ttl} seconds")
    
    # Try to get Redis info if available
    try:
        from backend.utils.cache import _get_redis_client
        redis_client = _get_redis_client()
        if redis_client:
            info = redis_client.info()
            click.echo(f"Redis used memory: {info.get('used_memory_human', 'N/A')}")
            click.echo(f"Redis connected clients: {info.get('connected_clients', 'N/A')}")
        else:
            click.echo("Redis: Not connected")
    except Exception:
        click.echo("Redis: Info unavailable")


@cli.command("cache-clear")
@with_appcontext
@click.option("--prefix", help="Clear cache entries with specific prefix")
def cache_clear(prefix):
    """Clear cache entries"""
    from backend.utils.cache import cache_invalidate, _l1_cache
    
    if prefix:
        cache_invalidate(prefix)
        click.echo(f"Cleared cache entries with prefix: {prefix}")
    else:
        _l1_cache.clear()
        try:
            from backend.utils.cache import _get_redis_client
            redis_client = _get_redis_client()
            if redis_client:
                redis_client.flushdb()
                click.echo("Cleared all cache entries (L1 + Redis)")
            else:
                click.echo("Cleared L1 cache only")
        except Exception:
            click.echo("Cleared L1 cache only")


@cli.command("analyze-crypto")
@with_appcontext
@click.argument("symbol")
@click.option("--timeframe", default="1d", help="Analysis timeframe")
@click.option("--enhanced", is_flag=True, help="Use enhanced analysis task")
def analyze_crypto(symbol, timeframe, enhanced):
    """Trigger crypto analysis task"""
    if enhanced:
        from backend.tasks.celery_tasks import analyze_crypto_symbol_enhanced
        task = analyze_crypto_symbol_enhanced.delay(symbol, timeframe)
    else:
        from backend.tasks.celery_tasks import analyze_coin_task
        task = analyze_coin_task.delay(symbol, "moderate")
    
    click.echo(f"Analysis task queued for {symbol}")
    click.echo(f"Task ID: {task.id}")


@cli.command("cleanup-tasks")
@with_appcontext
def cleanup_tasks():
    """Clean up stale task records"""
    from backend.tasks.celery_tasks import cleanup_stale_tasks
    
    task = cleanup_stale_tasks.delay()
    click.echo(f"Cleanup task queued. Task ID: {task.id}")


@cli.command("health-check")
@with_appcontext
def health_check():
    """Check system health"""
    from flask import current_app
    import requests
    
    # Check database
    try:
        from backend.db import db
        db.session.execute("SELECT 1")
        click.echo("✓ Database: Connected")
    except Exception as e:
        click.echo(f"✗ Database: {e}")
    
    # Check Redis
    try:
        from backend.utils.cache import _get_redis_client
        redis_client = _get_redis_client()
        if redis_client:
            redis_client.ping()
            click.echo("✓ Redis: Connected")
        else:
            click.echo("✗ Redis: Not connected")
    except Exception as e:
        click.echo(f"✗ Redis: {e}")
    
    # Check Celery
    try:
        from backend.tasks.celery_tasks import celery_app
        inspect = celery_app.control.inspect()
        stats = inspect.stats()
        if stats:
            click.echo("✓ Celery: Workers active")
            for worker, info in stats.items():
                click.echo(f"  - {worker}: {info.get('total', 0)} tasks processed")
        else:
            click.echo("✗ Celery: No workers found")
    except Exception as e:
        click.echo(f"✗ Celery: {e}")
    
    # Check API health
    try:
        base_url = current_app.config.get('API_BASE_PREFIX', '/api/v1')
        response = requests.get(f"http://localhost:5000{base_url}/health", timeout=5)
        if response.status_code == 200:
            click.echo("✓ API: Responsive")
        else:
            click.echo(f"✗ API: Status {response.status_code}")
    except Exception as e:
        click.echo(f"✗ API: {e}")


@cli.command("config-validate")
@with_appcontext
def config_validate():
    """Validate configuration"""
    from flask import current_app
    
    click.echo("Configuration Validation:")
    
    # Check required config values
    required_configs = [
        'SECRET_KEY', 'SQLALCHEMY_DATABASE_URI', 'REDIS_URL'
    ]
    
    for key in required_configs:
        value = current_app.config.get(key)
        if value:
            # Mask sensitive values
            if 'SECRET' in key or 'PASSWORD' in key:
                masked = f"{value[:4]}***{value[-4:]}" if len(value) > 8 else "***"
                click.echo(f"✓ {key}: {masked}")
            else:
                click.echo(f"✓ {key}: {value}")
        else:
            click.echo(f"✗ {key}: Not set")
    
    # Check optional enhanced features
    optional_configs = [
        'SENTRY_DSN', 'CACHE_REDIS_URL', 'API_TITLE'
    ]
    
    click.echo("\nOptional Features:")
    for key in optional_configs:
        value = current_app.config.get(key)
        status = "✓" if value else "○"
        click.echo(f"{status} {key}: {'Configured' if value else 'Not configured'}")


@cli.command("metrics")
@with_appcontext
def metrics():
    """Show system metrics"""
    from backend.utils.cache import _l1_cache
    from backend.tasks.celery_tasks import get_dlq_size
    
    click.echo("System Metrics:")
    click.echo(f"L1 Cache entries: {len(_l1_cache)}")
    click.echo(f"DLQ size: {get_dlq_size()}")
    
    # Database metrics
    try:
        from backend.db import db
        from backend.db.models import CeleryTaskLog
        
        total_tasks = db.session.query(CeleryTaskLog).count()
        recent_tasks = db.session.query(CeleryTaskLog).filter(
            CeleryTaskLog.created_at > db.func.now() - db.text("INTERVAL '24 hours'")
        ).count()
        
        click.echo(f"Total tasks (all time): {total_tasks}")
        click.echo(f"Tasks (last 24h): {recent_tasks}")
    except Exception as e:
        click.echo(f"Database metrics unavailable: {e}")


@cli.command()
@click.option("--host", default="0.0.0.0")
@click.option("--port", default=5000, type=int)
@click.option("--debug", is_flag=True)
def runserver(host: str, port: int, debug: bool):
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    cli()
