.PHONY: ensure-env env-check

ensure-env:
@echo ">> Ensuring .env.example contains all required keys"
@python3 scripts/ensure_env_keys.py --apply

env-check:
@python3 scripts/ensure_env_keys.py --check
