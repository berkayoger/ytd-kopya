# Repository Guidelines

## Project Structure & Module Organization
- `backend/`: Flask app factory, blueprints, security, tasks, and utils.
- `app/`: security wrappers and app bootstrap helpers (e.g., `secure_app.py`).
- `frontend/`: static pages/assets; optionally served via Flask or Nginx.
- `scripts/`: utilities (e.g., `ensure_env_keys.py`, `security_check.py`, `rotate_jwt_secret.py`).
- `tests/`: Pytest suite (`test_*.py`).
- `wsgi.py`: local entrypoint (creates the Flask app).

## Build, Test, and Development Commands
- Setup env keys: `make ensure-env` or `python scripts/ensure_env_keys.py --apply`.
- Install deps: `pip install -r backend/requirements.txt` (dev extras: `-r requirements-dev.txt`).
- Run locally: `FLASK_ENV=development python wsgi.py` (serves on `http://localhost:5000`).
- Docker (optional): `docker-compose up --build`.
- Tests: `pytest` or with coverage `pytest --cov=backend tests/`.
- Security quick check: `python scripts/security_check.py`.

## Coding Style & Naming Conventions
- Formatter: Black; Imports: isort; Lint: flake8 (line length 100). Install pre-commit and run: `pre-commit install && pre-commit run -a`.
- Indentation: 4 spaces. Modules/functions: `snake_case`; Classes: `PascalCase`; Constants: `UPPER_SNAKE_CASE`.
- Files and packages use lowercase with underscores (e.g., `utils/logger.py`).

## Testing Guidelines
- Framework: Pytest. Test files: `tests/test_*.py` (configured in `pytest.ini`).
- Keep tests deterministic; prefer fixtures over global state. Mock network and heavy imports when possible.
- Aim for meaningful coverage on `backend/` core logic. Example: `pytest -q` for quick runs.

## Commit & Pull Request Guidelines
- Commits: Prefer Conventional Commits (e.g., `feat:`, `fix:`, `refactor:`, `build(ci):`).
- PRs: clear description, linked issues, steps to verify, and screenshots/GIFs for UI changes.
- Requirements: passing CI, updated docs if behavior/config changes, and added/updated tests for logic changes.

## Security & Configuration Tips
- Use `.env.example` as the source of truth; check with `make env-check`.
- Production: prefer a secrets manager for sensitive values. Hardened WSGI entrypoints are available (see `app/secure_app.py`); for dev use `python wsgi.py`, for prod a WSGI server like Gunicorn (`gunicorn 'wsgi:app'`).
