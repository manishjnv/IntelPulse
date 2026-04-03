#!/usr/bin/env python3
"""Validate security configuration before deployment."""

import os
import sys
from pathlib import Path


def check_env_file():
    """Check if .env file exists and is not in git."""
    if not Path(".env").exists():
        print("❌ .env file not found")
        print("   Run: cp .env.production.example .env")
        return False
    
    gitignore = Path(".gitignore").read_text()
    if ".env" not in gitignore:
        print("❌ .env is not in .gitignore")
        print("   Add .env to .gitignore immediately!")
        return False
    
    print("✅ .env file exists and is gitignored")
    return True


def check_secret(name, min_length=32):
    """Check if a secret is set and meets minimum requirements."""
    value = os.getenv(name, "")
    
    if not value:
        print(f"❌ {name} is not set")
        return False
    
    # Check for default/weak values
    weak_values = [
        "change-me", "changeme", "secret", "password", "admin",
        "ti_secret", "dev-secret", "dev-only", "T1_Pl@tf0rm_2024!"
    ]
    if any(weak in value.lower() for weak in weak_values):
        print(f"❌ {name} contains a weak/default value")
        return False
    
    if len(value) < min_length:
        print(f"❌ {name} is too short (min {min_length} chars)")
        return False
    
    print(f"✅ {name} is set and strong")
    return True


def check_cors():
    """Check CORS configuration."""
    cors = os.getenv("CORS_ORIGINS", "")
    
    if not cors:
        print("⚠️  CORS_ORIGINS not set (will use defaults)")
        return True
    
    if "*" in cors:
        print("❌ CORS_ORIGINS contains wildcard (*)")
        print("   This is insecure with credentials enabled!")
        return False
    
    origins = [o.strip() for o in cors.split(",")]
    if not all(o.startswith("https://") or o.startswith("http://localhost") for o in origins):
        print("⚠️  CORS_ORIGINS contains non-HTTPS origins")
        print("   Ensure HTTPS is used in production")
    
    print(f"✅ CORS_ORIGINS configured: {len(origins)} origins")
    return True


def check_environment():
    """Check environment setting."""
    env = os.getenv("ENVIRONMENT", "development")
    
    if env == "production":
        print("✅ ENVIRONMENT=production")
        return True
    else:
        print(f"⚠️  ENVIRONMENT={env} (not production)")
        return True


def main():
    """Run all security checks."""
    print("=" * 60)
    print("IntelPulse Security Configuration Validator")
    print("=" * 60)
    print()
    
    # Load .env if it exists
    env_file = Path(".env")
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ[key.strip()] = value.strip()
    
    checks = [
        ("Environment File", check_env_file),
        ("Environment Setting", check_environment),
        ("SECRET_KEY", lambda: check_secret("SECRET_KEY", 32)),
        ("POSTGRES_PASSWORD", lambda: check_secret("POSTGRES_PASSWORD", 16)),
        ("REDIS_PASSWORD", lambda: check_secret("REDIS_PASSWORD", 16)),
        ("CORS Configuration", check_cors),
    ]
    
    results = []
    for name, check_func in checks:
        print(f"\nChecking: {name}")
        print("-" * 60)
        results.append(check_func())
    
    print()
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"✅ All checks passed ({passed}/{total})")
        print()
        print("Your configuration is secure and ready for deployment!")
        return 0
    else:
        print(f"❌ {total - passed} check(s) failed ({passed}/{total} passed)")
        print()
        print("Please fix the issues above before deploying to production.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
