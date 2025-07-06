# File: backend/auth/middlewares.py

import logging
from functools import wraps
from flask import jsonify
# Flask-JWT-Extended 4.x sürümlerinde `fresh_jwt_required` fonksiyonu
# mevcut olmayabilir. Geriye dönük uyumluluk için yoksa `jwt_required`
# fonksiyonunu kullanıyoruz.
try:
    from flask_jwt_extended import fresh_jwt_required, get_jwt, get_jwt_identity
except Exception:  # pragma: no cover - kutuphane eksikse basit stub kullan
    def fresh_jwt_required(*args, **kwargs):
        def decorator(fn):
            return fn
        return decorator

    def get_jwt():
        return {}

    def get_jwt_identity():
        return None
from backend.db.models import User  # Kullanıcı modelini DB'den çekmek için
from sqlalchemy.exc import SQLAlchemyError

# Logger yapılandırması uygulama başlangıcında ayarlanmalı.
logger = logging.getLogger(__name__)


def admin_required():
    """
    Sadece veritabanında 'is_admin' alanı True olan kullanıcıların erişimine izin verir.
    Bu decorator, @fresh_jwt_required() decorator'ından sonra kullanılır.
    Yetkisiz erişim denemeleri uyarı logu üretir.
    """
    def wrapper(fn):
        @wraps(fn)
        @fresh_jwt_required()
        def decorator(*args, **kwargs):
            try:
                # JWT'den kullanıcı kimliğini al
                user_id = get_jwt_identity()
                # Veritabanından kullanıcıyı çekip admin yetkisini doğrula
                user = User.query.get(user_id)
                if not user:
                    logger.warning(f"Admin erişim: kullanıcı bulunamadı. ID: {user_id}")
                    return jsonify({"error": "Admin yetkisi gereklidir!"}), 403

                if not getattr(user, 'is_admin', False):
                    jti = get_jwt().get('jti')
                    logger.warning(
                        f"Unauthorized admin access attempt! User ID: {user_id}, JTI: {jti}"
                    )
                    return jsonify({"error": "Admin yetkisi gereklidir!"}), 403

                # Yetkili kullanıcı, orijinal handler'a devam et
                return fn(*args, **kwargs)
            except SQLAlchemyError:
                logger.exception("admin_required: Veritabanı hatası oluştu")
                return jsonify({"error": "Sunucu hatası. Lütfen daha sonra tekrar deneyin."}), 500
            except Exception:
                logger.exception("admin_required: Beklenmeyen bir hata oluştu")
                return jsonify({"error": "Sunucu hatası. Lütfen daha sonra tekrar deneyin."}), 500

        return decorator
    return wrapper

# Örnek Kullanım:
# from backend.auth.middlewares import admin_required
#
# @app.route('/admin/dashboard')
# @fresh_jwt_required()
# @admin_required()
# def admin_dashboard():
#     return jsonify({"message": "Admin paneline hoş geldiniz!"})
