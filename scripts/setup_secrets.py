#!/usr/bin/env python3
"""
Gizli Bilgi Kurulum Aracı
Hassas yapılandırma değerlerini üretir ve şifreler
"""

import argparse
import base64
import os
import secrets
import sys
from pathlib import Path

# Proje kökünü import yoluna ekle
sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.secrets_manager import SecretsManager  # type: ignore


def generate_secret_key() -> str:
    """Güvenli SECRET_KEY üret"""
    return secrets.token_urlsafe(32)


def generate_jwt_secret() -> str:
    """Güvenli JWT anahtarı üret"""
    return secrets.token_urlsafe(64)


def generate_encryption_key() -> str:
    """Şifreleme anahtarı üret"""
    return base64.urlsafe_b64encode(os.urandom(32)).decode()


def setup_development_env() -> None:
    """Geliştirme ortamı için .env dosyası oluştur"""
    env_file = Path(".env")
    if env_file.exists():
        response = input(".env dosyası zaten var. Üzerine yazılsın mı? (y/N): ")
        if response.lower() != "y":
            print("İptal edildi.")
            return
    config = {
        "FLASK_ENV": "development",
        "FLASK_DEBUG": "True",
        "SECRET_KEY": generate_secret_key(),
        "JWT_SECRET_KEY": generate_jwt_secret(),
        "ENCRYPTION_KEY": generate_encryption_key(),
        "DATABASE_URL": "sqlite:///app.db",
        "REDIS_URL": "redis://localhost:6379/0",
        "LOG_LEVEL": "INFO",
        "LOG_FILE": "logs/app.log",
        "RATE_LIMIT_DEFAULT": "100/minute",
    }
    with open(env_file, "w") as f:
        f.write("# Otomatik oluşturulan geliştirme yapılandırması\n")
        f.write("# setup_secrets.py tarafından üretildi\n\n")
        for key, value in config.items():
            f.write(f"{key}={value}\n")
    print(f"Geliştirme ortamı {env_file} içerisine yazıldı")
    print("Lütfen API anahtarlarını manuel olarak ekleyin:")
    print("- COINGECKO_API_KEY")
    print("- CRYPTOCOMPARE_API_KEY")


def encrypt_env_file(input_file: str, output_file: str, encryption_key: str) -> None:
    """Bir .env dosyasını şifrele"""
    if not Path(input_file).exists():
        print(f"Hata: giriş dosyası {input_file} bulunamadı")
        return
    try:
        manager = SecretsManager(encryption_key)
        manager.encrypt_env_file(input_file, output_file)
        print(f"Env dosyası şifrelendi: {input_file} -> {output_file}")
    except Exception as exc:  # pragma: no cover - kullanıcı girdisi
        print(f"Dosya şifrelenemedi: {exc}")


def validate_env_file(env_file: str) -> None:
    """Bir .env dosyasını güvenlik açısından doğrula"""
    path = Path(env_file)
    if not path.exists():
        print(f"Hata: {env_file} bulunamadı")
        return
    issues = []
    with open(path, "r") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            weak_values = {"password", "123456", "admin", "test", "changeme"}
            if value in weak_values:
                issues.append(f"Satır {line_num}: {key} zayıf bir değer içeriyor")
            if "your-" in value.lower() or "change-me" in value.lower():
                issues.append(f"Satır {line_num}: {key} varsayılan yer tutucu içeriyor")
            if any(pat in key.upper() for pat in ["SECRET", "KEY", "PASSWORD"]):
                if len(value) < 16:
                    issues.append(
                        f"Satır {line_num}: {key} çok kısa (en az 16 karakter)"
                    )
    if issues:
        print("Güvenlik sorunları bulundu:")
        for issue in issues:
            print(f"- {issue}")
    else:
        print("Sorun tespit edilmedi.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Gizli değer kurulum aracı")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("init", help="Geliştirme .env dosyası oluştur")

    enc = sub.add_parser("encrypt", help=".env dosyasını şifrele")
    enc.add_argument("input", help="Giriş .env dosyası")
    enc.add_argument("output", help="Şifreli çıktı dosyası")
    enc.add_argument("key", help="ENCRYPTION_KEY değeri")

    val = sub.add_parser("validate", help=".env dosyasını doğrula")
    val.add_argument("file", help="Kontrol edilecek dosya")

    args = parser.parse_args()
    if args.command == "init":
        setup_development_env()
    elif args.command == "encrypt":
        encrypt_env_file(args.input, args.output, args.key)
    elif args.command == "validate":
        validate_env_file(args.file)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
