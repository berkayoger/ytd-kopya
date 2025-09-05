import asyncio
import logging
import os
from flask import Flask
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import redis

from .services.security_optimization_service import (
    SecurityOptimizationService, SecurityConfig, OptimizationConfig,
    create_security_optimization_service
)
from .config import get_config
from .utils.logging_setup import setup_logging
from .db import db as db

# Logging setup
logger = logging.getLogger(__name__)

# Global service instance
security_service: SecurityOptimizationService = None
socketio = None

def create_app(config_name: str = None) -> Flask:
    """Flask uygulaması oluştur ve güvenlik sistemini entegre et"""
    
    # Flask app oluştur
    app = Flask(__name__)
    
    # Config yükle
    config_name = config_name or os.getenv('FLASK_ENV', 'development')
    config = get_config(config_name)
    app.config.from_object(config)
    
    # Logging setup
    setup_logging(app.config.get('LOG_LEVEL', 'INFO'))
    
    # CORS setup
    CORS(app, resources={
        r"/api/*": {
            "origins": app.config.get('ALLOWED_ORIGINS') or app.config.get('CORS_ORIGINS', ["http://localhost:3000"]),
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization", "X-CSRF-Token"]
        }
    })
    
    # Rate Limiter setup (Flask-Limiter v3 compatible)
    limiter = Limiter(
        key_func=get_remote_address,
        default_limits=["200 per day", "50 per hour"],
        storage_uri=app.config.get('REDIS_URL', 'memory://')
    )
    limiter.init_app(app)
    
    # Register blueprints
    register_blueprints(app)
    
    # Development tables
    setup_development_tables(app)
    
    # Initialize security service synchronously to avoid loop conflicts
    try:
        global security_service
        security_service = setup_security_service_sync(app)
    except Exception as e:
        logger.error(f"Failed to setup security service: {e}")
    
    # Health check endpoint
    @app.route('/health')
    def health_check():
        """Sistem sağlık kontrolü"""
        if security_service:
            status = security_service.get_service_status()
            return status.__dict__, 200 if getattr(status, 'is_healthy', False) else 503
        return {'status': 'service_not_initialized'}, 503
    
    # Security dashboard endpoints
    register_security_endpoints(app)
    
    # Error handlers
    register_error_handlers(app)
    
    return app

def setup_development_tables(app):
    """Development ortamında tabloları otomatik oluştur"""
    if app.config.get('FLASK_ENV') == 'development':
        try:
            from .db import db
            with app.app_context():
                db.create_all()
                print("Development tables created successfully")
        except Exception as e:
            print(f"Table creation failed: {e}")

async def setup_security_service(app: Flask):
    """Güvenlik servisini async olarak kur"""
    global security_service
    
    try:
        logger.info("Setting up security and optimization service...")
        
        # Service konfigürasyonu
        security_config = SecurityConfig(
            enable_sql_injection_protection=app.config.get('ENABLE_SQL_INJECTION_PROTECTION', True),
            enable_rate_limiting=app.config.get('ENABLE_RATE_LIMITING', True),
            enable_audit_logging=app.config.get('ENABLE_AUDIT_LOGGING', True),
            enable_query_monitoring=app.config.get('ENABLE_QUERY_MONITORING', True),
            slow_query_threshold=app.config.get('SLOW_QUERY_THRESHOLD', 1.0),
            max_query_execution_time=app.config.get('MAX_QUERY_EXECUTION_TIME', 30),
            rate_limit_per_minute=app.config.get('RATE_LIMIT_PER_MINUTE', 60),
            rate_limit_per_hour=app.config.get('RATE_LIMIT_PER_HOUR', 1000),
            enable_ip_whitelist=app.config.get('ENABLE_IP_WHITELIST', False),
            whitelisted_ips=app.config.get('WHITELISTED_IPS', []),
            enable_user_agent_filtering=app.config.get('ENABLE_USER_AGENT_FILTERING', True),
            blocked_user_agents=app.config.get('BLOCKED_USER_AGENTS', [
                'sqlmap', 'nikto', 'nmap', 'masscan', 'nessus'
            ])
        )
        
        optimization_config = OptimizationConfig(
            enable_query_caching=app.config.get('ENABLE_QUERY_CACHING', True),
            enable_result_pagination=app.config.get('ENABLE_RESULT_PAGINATION', True),
            enable_connection_pooling=app.config.get('ENABLE_CONNECTION_POOLING', True),
            enable_database_monitoring=app.config.get('ENABLE_DATABASE_MONITORING', True),
            enable_auto_indexing=app.config.get('ENABLE_AUTO_INDEXING', False),
            enable_maintenance_scheduler=app.config.get('ENABLE_MAINTENANCE_SCHEDULER', True),
            cache_ttl_seconds=app.config.get('CACHE_TTL_SECONDS', 300),
            max_connections=app.config.get('MAX_DB_CONNECTIONS', 20),
            connection_timeout=app.config.get('DB_CONNECTION_TIMEOUT', 30),
            query_cache_size=app.config.get('QUERY_CACHE_SIZE', 1000),
            enable_compression=app.config.get('ENABLE_COMPRESSION', True)
        )
        
        # Service oluştur ve başlat
        database_url = app.config.get('DATABASE_URL') or app.config.get('SQLALCHEMY_DATABASE_URI')
        security_service = SecurityOptimizationService(
            app=app,
            database_url=database_url,
            redis_url=app.config.get('REDIS_URL'),
            security_config=security_config,
            optimization_config=optimization_config
        )
        
        await security_service.initialize()
        
        # İlk optimizasyon çalıştır
        if app.config.get('RUN_INITIAL_OPTIMIZATION', True):
            optimization_result = await security_service.optimize_database()
            logger.info(f"Initial optimization completed: {len(optimization_result.get('index_recommendations', []))} recommendations")
        
        logger.info("Security and optimization service setup completed successfully")
        
    except Exception as e:
        logger.error(f"Failed to setup security service: {e}")
        raise

def setup_security_service_sync(app: Flask) -> SecurityOptimizationService:
    """Güvenlik servisini sync olarak kur ve event loop çakışmalarından kaçın."""
    logger.info("Setting up security and optimization service...")

    security_config = SecurityConfig(
        enable_sql_injection_protection=app.config.get('ENABLE_SQL_INJECTION_PROTECTION', True),
        enable_rate_limiting=app.config.get('ENABLE_RATE_LIMITING', True),
        enable_audit_logging=app.config.get('ENABLE_AUDIT_LOGGING', True),
        enable_query_monitoring=app.config.get('ENABLE_QUERY_MONITORING', True),
        slow_query_threshold=app.config.get('SLOW_QUERY_THRESHOLD', 1.0),
        max_query_execution_time=app.config.get('MAX_QUERY_EXECUTION_TIME', 30),
        rate_limit_per_minute=app.config.get('RATE_LIMIT_PER_MINUTE', 60),
        rate_limit_per_hour=app.config.get('RATE_LIMIT_PER_HOUR', 1000),
        enable_ip_whitelist=app.config.get('ENABLE_IP_WHITELIST', False),
        whitelisted_ips=app.config.get('WHITELISTED_IPS', []),
        enable_user_agent_filtering=app.config.get('ENABLE_USER_AGENT_FILTERING', True),
        blocked_user_agents=app.config.get('BLOCKED_USER_AGENTS', [
            'sqlmap', 'nikto', 'nmap', 'masscan', 'nessus'
        ])
    )

    optimization_config = OptimizationConfig(
        enable_query_caching=app.config.get('ENABLE_QUERY_CACHING', True),
        enable_result_pagination=app.config.get('ENABLE_RESULT_PAGINATION', True),
        enable_connection_pooling=app.config.get('ENABLE_CONNECTION_POOLING', True),
        enable_database_monitoring=app.config.get('ENABLE_DATABASE_MONITORING', True),
        enable_auto_indexing=app.config.get('ENABLE_AUTO_INDEXING', False),
        enable_maintenance_scheduler=app.config.get('ENABLE_MAINTENANCE_SCHEDULER', True),
        cache_ttl_seconds=app.config.get('CACHE_TTL_SECONDS', 300),
        max_connections=app.config.get('MAX_DB_CONNECTIONS', 20),
        connection_timeout=app.config.get('DB_CONNECTION_TIMEOUT', 30),
        query_cache_size=app.config.get('QUERY_CACHE_SIZE', 1000),
        enable_compression=app.config.get('ENABLE_COMPRESSION', True)
    )

    database_url = app.config.get('DATABASE_URL') or app.config.get('SQLALCHEMY_DATABASE_URI')
    service = SecurityOptimizationService(
        app=app,
        database_url=database_url,
        redis_url=app.config.get('REDIS_URL'),
        security_config=security_config,
        optimization_config=optimization_config
    )

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(service.initialize())
        else:
            asyncio.run(service.initialize())
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(service.initialize())
        loop.close()

    logger.info("Security and optimization service setup completed successfully")
    return service

def register_blueprints(app: Flask):
    """Blueprint'leri kaydet"""
    
    # API Blueprint
    from .api import api_bp
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # Auth Blueprint
    from .auth import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    
    # Admin Panel Blueprint
    from .admin_panel import admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')
    
    # Frontend Blueprint
    from .frontend import frontend_bp
    app.register_blueprint(frontend_bp)
    
    logger.info("Blueprints registered successfully")

def register_security_endpoints(app: Flask):
    """Güvenlik monitoring endpoint'lerini kaydet"""
    
    @app.route('/admin/security/report')
    def security_report():
        """Güvenlik raporu endpoint'i"""
        if not security_service:
            return {'error': 'Security service not initialized'}, 503
        
        try:
            report = security_service.get_security_report()
            return report
        except Exception as e:
            logger.error(f"Security report error: {e}")
            return {'error': str(e)}, 500
    
    @app.route('/admin/performance/report')
    def performance_report():
        """Performans raporu endpoint'i"""
        if not security_service or not getattr(security_service, 'db_optimizer', None):
            return {'error': 'Performance monitoring not available'}, 503
        
        try:
            report = security_service.db_optimizer.get_performance_report(hours=24)
            return report
        except Exception as e:
            logger.error(f"Performance report error: {e}")
            return {'error': str(e)}, 500
    
    @app.route('/admin/optimization/run', methods=['POST'])
    def run_optimization():
        """Database optimizasyonu çalıştır (sync wrapper)"""
        if not security_service:
            return {'error': 'Security service not initialized'}, 503

        try:
            result = asyncio.run(security_service.optimize_database())
            return result
        except Exception as e:
            logger.error(f"Optimization error: {e}")
            return {'error': str(e)}, 500
    
    @app.route('/admin/cleanup/old-data', methods=['POST'])
    def cleanup_old_data():
        """Eski verileri temizle (sync wrapper)"""
        if not security_service:
            return {'error': 'Security service not initialized'}, 503

        try:
            from flask import request
            days = request.json.get('days', 90) if request.is_json else 90
            result = asyncio.run(security_service.cleanup_old_data(days=days))
            return result
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
            return {'error': str(e)}, 500
    
    @app.route('/admin/monitoring/queries')
    def query_monitoring():
        """Query monitoring raporu"""
        if not security_service or not getattr(security_service, 'query_tracker', None):
            return {'error': 'Query monitoring not available'}, 503
        
        try:
            from .db.query_monitor import QueryPerformanceAnalyzer
            analyzer = QueryPerformanceAnalyzer(security_service.query_tracker)
            
            slow_queries = analyzer.analyze_slow_queries(hours=1)
            query_patterns = analyzer.analyze_query_patterns(hours=1)
            recommendations = analyzer.get_performance_recommendations()
            
            return {
                'slow_queries': slow_queries,
                'query_patterns': query_patterns,
                'recommendations': recommendations,
                'active_executions': len(security_service.query_tracker.get_active_executions())
            }
        except Exception as e:
            logger.error(f"Query monitoring error: {e}")
            return {'error': str(e)}, 500

def register_error_handlers(app: Flask):
    """Error handler'ları kaydet"""
    
    @app.errorhandler(400)
    def bad_request(error):
        """400 Bad Request handler"""
        logger.warning(f"Bad request: {error}")
        return {
            'error': 'Bad Request',
            'message': 'The request could not be understood by the server',
            'code': 400
        }, 400
    
    @app.errorhandler(401)
    def unauthorized(error):
        """401 Unauthorized handler"""
        logger.warning(f"Unauthorized access: {error}")
        return {
            'error': 'Unauthorized',
            'message': 'Authentication required',
            'code': 401
        }, 401
    
    @app.errorhandler(403)
    def forbidden(error):
        """403 Forbidden handler"""
        logger.warning(f"Forbidden access: {error}")
        return {
            'error': 'Forbidden',
            'message': 'Access denied',
            'code': 403
        }, 403
    
    @app.errorhandler(404)
    def not_found(error):
        """404 Not Found handler"""
        return {
            'error': 'Not Found',
            'message': 'The requested resource was not found',
            'code': 404
        }, 404
    
    @app.errorhandler(429)
    def rate_limit_exceeded(error):
        """429 Rate Limit Exceeded handler"""
        logger.warning(f"Rate limit exceeded: {error}")
        return {
            'error': 'Rate Limit Exceeded',
            'message': 'Too many requests, please try again later',
            'code': 429,
            'retry_after': getattr(error, 'retry_after', 60)
        }, 429
    
    @app.errorhandler(500)
    def internal_server_error(error):
        """500 Internal Server Error handler"""
        logger.error(f"Internal server error: {error}")
        
        # Database rollback
        from flask import g
        if hasattr(g, 'db_session'):
            try:
                g.db_session.rollback()
            except Exception:
                pass
        
        return {
            'error': 'Internal Server Error',
            'message': 'An unexpected error occurred',
            'code': 500
        }, 500
    
    @app.errorhandler(Exception)
    def handle_exception(error):
        """Genel exception handler"""
        logger.error(f"Unhandled exception: {error}", exc_info=True)
        
        # Database rollback
        from flask import g
        if hasattr(g, 'db_session'):
            try:
                g.db_session.rollback()
            except Exception:
                pass
        
        return {
            'error': 'Internal Server Error',
            'message': 'An unexpected error occurred',
            'code': 500
        }, 500


# CLI Commands
def register_cli_commands(app: Flask):
    """CLI komutlarını kaydet"""
    import click
    
    @app.cli.command('init-db')
    def init_db_command():
        """Database'i başlat"""
        try:
            asyncio.run(init_database(app))
            print("Database initialized successfully.")
        except Exception as e:
            print(f"Database initialization failed: {e}")
    
    @app.cli.command('create-indexes')
    def create_indexes_command():
        """Index'leri oluştur"""
        try:
            asyncio.run(create_database_indexes(app))
            print("Indexes created successfully.")
        except Exception as e:
            print(f"Index creation failed: {e}")
    
    @app.cli.command('optimize-db')
    def optimize_db_command():
        """Database optimizasyonu çalıştır"""
        try:
            asyncio.run(run_database_optimization(app))
        except Exception as e:
            print(f"Database optimization failed: {e}")
    
    @app.cli.command('security-report')
    def security_report_command():
        """Güvenlik raporu oluştur"""
        try:
            asyncio.run(generate_security_report(app))
        except Exception as e:
            print(f"Security report generation failed: {e}")
    
    @app.cli.command('cleanup-data')
    @click.option('--days', default=90, help='Number of days to keep data')
    def cleanup_data_command(days):
        """Eski verileri temizle"""
        try:
            asyncio.run(cleanup_old_data(app, days))
        except Exception as e:
            print(f"Data cleanup failed: {e}")


# CLI Helper Functions
async def init_database(app: Flask):
    """Database initialization"""
    try:
        from .db.models import Base, create_all_indexes, setup_database_functions
        from sqlalchemy import create_engine
    except Exception:
        # Optional import fallback
        return
    
    engine = create_engine(app.config.get('DATABASE_URL') or app.config.get('SQLALCHEMY_DATABASE_URI'))
    
    # Create tables
    Base.metadata.create_all(engine)
    print("Tables created.")
    
    # Create indexes
    create_all_indexes(engine)
    print("Indexes created.")
    
    # Setup database functions
    setup_database_functions(engine)
    print("Database functions created.")
    
    engine.dispose()

async def create_database_indexes(app: Flask):
    """Database index creation"""
    try:
        from .db.optimization import create_database_optimizer
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
    except Exception:
        return
    
    engine = create_engine(app.config.get('DATABASE_URL') or app.config.get('SQLALCHEMY_DATABASE_URI'))
    session_factory = sessionmaker(bind=engine)
    
    optimizer = create_database_optimizer(engine, session_factory)
    recommendations = optimizer.get_index_recommendations()
    
    print(f"Found {len(recommendations)} index recommendations:")
    
    for i, rec in enumerate(recommendations[:10], 1):
        print(f"{i}. {rec.table_name}.{rec.columns} - {rec.reason}")
        
        # Create high priority indexes
        if rec.priority >= 4:
            try:
                success = await optimizer.create_index_online(rec)
                if success:
                    print(f"   ✓ Created index for {rec.table_name}.{rec.columns}")
                else:
                    print(f"   ✗ Failed to create index for {rec.table_name}.{rec.columns}")
            except Exception as e:
                print(f"   ✗ Error creating index: {e}")
    
    engine.dispose()

async def run_database_optimization(app: Flask):
    """Database optimization"""
    config_dict = {
        'DATABASE_URL': app.config.get('DATABASE_URL') or app.config.get('SQLALCHEMY_DATABASE_URI'),
        'REDIS_URL': app.config.get('REDIS_URL'),
        'ENABLE_AUTO_INDEXING': True
    }
    
    service = create_security_optimization_service(app, config_dict)
    await service.initialize()
    
    try:
        result = await service.optimize_database()
        
        print("Database Optimization Report:")
        print("=" * 50)
        
        if 'index_recommendations' in result:
            print(f"Index Recommendations: {len(result['index_recommendations'])}")
            for rec in result['index_recommendations'][:5]:
                print(f"  - {rec['table']}.{rec['columns']}: {rec['reason']}")
        
        if 'slow_queries_analysis' in result:
            print(f"\nSlow Queries Found: {len(result['slow_queries_analysis'])}")
            for sq in result['slow_queries_analysis'][:3]:
                print(f"  - {sq['execution_time']:.3f}s: {sq['query'][:100]}...")
        
        if 'auto_created_indexes' in result:
            print(f"\nAuto-created Indexes: {len(result['auto_created_indexes'])}")
            for idx in result['auto_created_indexes']:
                print(f"  - {idx}")
        
        print(f"\nPerformance Summary:")
        summary = result.get('performance_summary', {})
        for key, value in summary.items():
            print(f"  {key}: {value}")
            
    finally:
        await service.shutdown()

async def generate_security_report(app: Flask):
    """Generate security report"""
    config_dict = {
        'DATABASE_URL': app.config.get('DATABASE_URL') or app.config.get('SQLALCHEMY_DATABASE_URI'),
        'REDIS_URL': app.config.get('REDIS_URL')
    }
    
    service = create_security_optimization_service(app, config_dict)
    await service.initialize()
    
    try:
        report = service.get_security_report()
        
        print("Security Report:")
        print("=" * 50)
        print(f"Report Time: {report['report_timestamp']}")
        print(f"Security Events (24h): {report['security_events_24h']}")
        print(f"Failed Logins (24h): {report['failed_logins_24h']}")
        print(f"Suspicious Queries: {report['suspicious_queries']}")
        
        if report['suspicious_ips']:
            print(f"\nTop Suspicious IPs:")
            for ip, count in list(report['suspicious_ips'].items())[:5]:
                print(f"  {ip}: {count} failed attempts")
        
        print(f"\nSecurity Configuration:")
        config_info = report['security_config']
        for key, value in config_info.items():
            status = "✓" if value else "✗"
            print(f"  {status} {key}: {value}")
        
        if report['top_security_events']:
            print(f"\nRecent Security Events:")
            for event in report['top_security_events'][:5]:
                print(f"  {event['timestamp']}: {event['action']} from {event['ip_address']}")
                
    finally:
        await service.shutdown()

async def cleanup_old_data(app: Flask, days: int):
    """Cleanup old data"""
    config_dict = {
        'DATABASE_URL': app.config.get('DATABASE_URL') or app.config.get('SQLALCHEMY_DATABASE_URI'),
        'REDIS_URL': app.config.get('REDIS_URL')
    }
    
    service = create_security_optimization_service(app, config_dict)
    await service.initialize()
    
    try:
        result = await service.cleanup_old_data(days=days)
        
        print(f"Data Cleanup Report (keeping last {days} days):")
        print("=" * 50)
        print(f"Cleanup Time: {result['cleanup_timestamp']}")
        print(f"Deleted Audit Logs: {result['deleted_audit_logs']}")
        print(f"Deleted Expired Sessions: {result['deleted_expired_sessions']}")
        print(f"Deleted Rate Limits: {result['deleted_rate_limits']}")
        
    finally:
        await service.shutdown()


# Graceful shutdown
def setup_graceful_shutdown(app: Flask):
    """Graceful shutdown setup"""
    import signal
    import sys
    
    def signal_handler(sig, frame):
        logger.info("Received shutdown signal, cleaning up...")
        
        # Shutdown security service
        if security_service:
            try:
                asyncio.run(security_service.shutdown())
            except Exception as e:
                logger.error(f"Error during service shutdown: {e}")
        
        logger.info("Shutdown complete")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


# Production deployment helpers
def create_production_app() -> Flask:
    """Production için optimize edilmiş Flask uygulaması"""
    app = create_app('production')
    
    # Production specific configurations
    app.config.update({
        'ENABLE_SQL_INJECTION_PROTECTION': True,
        'ENABLE_RATE_LIMITING': True,
        'ENABLE_AUDIT_LOGGING': True,
        'ENABLE_QUERY_MONITORING': True,
        'ENABLE_DATABASE_MONITORING': True,
        'ENABLE_MAINTENANCE_SCHEDULER': True,
        'SLOW_QUERY_THRESHOLD': 0.5,  # Daha strict
        'RATE_LIMIT_PER_MINUTE': 30,  # Daha strict
        'RATE_LIMIT_PER_HOUR': 500,   # Daha strict
        'ENABLE_USER_AGENT_FILTERING': True,
        'ENABLE_COMPRESSION': True,
        'MAX_DB_CONNECTIONS': 30,
        'CACHE_TTL_SECONDS': 600,     # 10 dakika
    })
    
    # CLI commands
    register_cli_commands(app)
    
    # Graceful shutdown
    setup_graceful_shutdown(app)
    
    return app


# Development helpers
def create_development_app() -> Flask:
    """Development için optimize edilmiş Flask uygulaması"""
    app = create_app('development')
    
    # Development specific configurations
    app.config.update({
        'ENABLE_SQL_INJECTION_PROTECTION': True,
        'ENABLE_RATE_LIMITING': False,  # Development'ta kapalı
        'ENABLE_AUDIT_LOGGING': True,
        'ENABLE_QUERY_MONITORING': True,
        'ENABLE_DATABASE_MONITORING': True,
        'ENABLE_MAINTENANCE_SCHEDULER': False,  # Development'ta kapalı
        'SLOW_QUERY_THRESHOLD': 2.0,   # Daha toleranslı
        'ENABLE_AUTO_INDEXING': False,  # Güvenlik için kapalı
        'MAX_DB_CONNECTIONS': 5,
        'CACHE_TTL_SECONDS': 60,
    })
    
    # CLI commands
    register_cli_commands(app)
    
    return app


# Testing helpers
def create_test_app() -> Flask:
    """Test için optimize edilmiş Flask uygulaması"""
    app = create_app('testing')
    
    # Testing specific configurations
    app.config.update({
        'ENABLE_SQL_INJECTION_PROTECTION': True,
        'ENABLE_RATE_LIMITING': False,
        'ENABLE_AUDIT_LOGGING': False,
        'ENABLE_QUERY_MONITORING': False,
        'ENABLE_DATABASE_MONITORING': False,
        'ENABLE_MAINTENANCE_SCHEDULER': False,
        'MAX_DB_CONNECTIONS': 2,
        'CACHE_TTL_SECONDS': 10,
    })
    
    return app


# Export functions
__all__ = [
    'create_app',
    'create_production_app',
    'create_development_app', 
    'create_test_app',
    'setup_security_service',
    'setup_security_service_sync',
    'security_service',
    'socketio',
    'db',
    'register_blueprints',
    'register_security_endpoints',
    'register_error_handlers',
    'register_cli_commands'
]
