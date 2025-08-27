#!/usr/bin/env python3
"""
Security Check Script for YTD Crypto Application

This script performs basic security validations on the application configuration.
"""

import os
import sys
import re
from pathlib import Path

def check_env_security():
    """Check environment configuration security"""
    issues = []
    env_file = Path('.env')
    if not env_file.exists():
        issues.append("❌ .env file not found. Copy .env.example to .env")
        return issues
    with open(env_file) as f:
        env_content = f.read()
    jwt_secret_match = re.search(r'JWT_SECRET_KEY=(.+)', env_content)
    if not jwt_secret_match:
        issues.append("❌ JWT_SECRET_KEY not set in .env")
    else:
        jwt_secret = jwt_secret_match.group(1).strip()
        if len(jwt_secret) < 32:
            issues.append("❌ JWT_SECRET_KEY is too short (minimum 32 characters)")
        if jwt_secret == 'your-jwt-secret-key-at-least-64-characters-long-for-production':
            issues.append("❌ JWT_SECRET_KEY is using example value")
    secret_match = re.search(r'SECRET_KEY=(.+)', env_content)
    if not secret_match:
        issues.append("❌ SECRET_KEY not set in .env")
    else:
        secret = secret_match.group(1).strip()
        if secret == 'your-secret-key-here':
            issues.append("❌ SECRET_KEY is using example value")
    if 'REDIS_PASSWORD=' not in env_content or 'REDIS_PASSWORD=your-redis-password' in env_content:
        issues.append("⚠️  Redis password not set (recommended for production)")
    if 'DATABASE_URL=sqlite' in env_content:
        issues.append("⚠️  Using SQLite database (consider PostgreSQL for production)")
    return issues

def check_file_permissions():
    """Check file permissions"""
    issues = []
    env_file = Path('.env')
    if env_file.exists():
        stat_info = env_file.stat()
        if stat_info.st_mode & 0o044:
            issues.append("❌ .env file has overly permissive permissions")
    return issues

def check_dependencies():
    """Check for security-related dependencies"""
    issues = []
    requirements_file = Path('backend/requirements.txt')
    if not requirements_file.exists():
        issues.append("❌ requirements.txt not found")
        return issues
    with open(requirements_file) as f:
        requirements = f.read()
    security_deps = ['cryptography', 'bcrypt', 'user-agents']
    for dep in security_deps:
        if dep not in requirements:
            issues.append(f"⚠️  Security dependency '{dep}' not found in requirements.txt")
    return issues

def main():
    """Run all security checks"""
    print("🔐 YTD Crypto Application Security Check")
    print("=" * 50)
    all_issues = []
    print("\n📋 Checking environment configuration...")
    all_issues.extend(check_env_security())
    print("\n📁 Checking file permissions...")
    all_issues.extend(check_file_permissions())
    print("\n📦 Checking dependencies...")
    all_issues.extend(check_dependencies())
    print("\n" + "=" * 50)
    if not all_issues:
        print("✅ All security checks passed!")
        return 0
    else:
        print(f"Found {len(all_issues)} security issues:")
        for issue in all_issues:
            print(f"  {issue}")
        print("\n🔧 Please address these issues before deploying to production.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
