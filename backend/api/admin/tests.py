from __future__ import annotations
import os, re, shlex, subprocess
from pathlib import Path
from flask import Blueprint, jsonify, request, g
from backend.auth.jwt_utils import jwt_required_if_not_testing
from backend.auth.middlewares import admin_required
from backend.utils.logger import create_log
from backend.observability.metrics import inc_error
from backend import limiter
from loguru import logger

admin_tests_bp = Blueprint("admin_tests", __name__, url_prefix="/api/admin/tests")

# Ortam değişkeni ile kapatılabilir
_ALLOW = os.getenv("ALLOW_ADMIN_TEST_RUN", "false").strip().lower() in {"1", "true", "yes", "on"}


def _project_root() -> Path:
    """
    Güvenli çalışma dizini: repo kökü tahmini.
    - Tercih: git projesi kökü
    - Değilse: backend klasörünün 1 üstü
    """
    here = Path(__file__).resolve()
    # git kökü ara
    for p in [here] + list(here.parents):
        if (p / ".git").exists() or (p / "pyproject.toml").exists() or (p / "pytest.ini").exists():
            return p if p.is_dir() else p.parent
    # yedek: backend klasörünün üstü
    for p in here.parents:
        if (p / "backend").exists():
            return p
    return here.parent


def _whitelisted_env() -> dict[str, str]:
    """
    Alt süreç için beyaz listeli environment.
    Gizli anahtarları taşımayız; test için yeterli minimum set.
    """
    allow: dict[str, str] = {}
    # Terminal çıktısı için faydalı
    for k in ("PATH", "PYTHONPATH", "TERM", "COLUMNS", "LINES"):
        if k in os.environ:
            allow[k] = os.environ[k]
    # Test modunda koşsun, bytecode yazmasın
    allow["FLASK_ENV"] = os.getenv("FLASK_ENV", "testing")
    allow["PYTHONDONTWRITEBYTECODE"] = "1"
    return allow


def _suite_to_pytest_args(suite: str) -> list[str]:
    """Verilen suite adını pytest argümanlarına çevir."""
    if suite == "smoke":
        return ["-q", "-k", "smoke", "--maxfail=1", "--disable-warnings"]
    if suite == "unit":
        return ["-q", "-k", "not e2e and not slow", "--disable-warnings"]
    return ["-q", "-k", "not e2e", "--disable-warnings"]


def _parse_summary(text: str) -> dict:
    """Pytest özet satırını ayrıştır."""
    m = re.search(r"=+ (.+?) =+\s*$", text, flags=re.M | re.S)
    summary = m.group(1).strip() if m else ""
    counts = {"passed": 0, "failed": 0, "errors": 0, "skipped": 0, "xfailed": 0, "xpassed": 0}
    for key in counts.keys():
        mm = re.search(rf"(\d+)\s+{key}", summary)
        if mm:
            counts[key] = int(mm.group(1))
    return {"raw": summary, **counts}


@admin_tests_bp.post("/run")
@jwt_required_if_not_testing()
@admin_required()
@limiter.limit("6/hour")
def run_tests():
    """Sunucu üzerinde testleri çalıştır."""
    if not _ALLOW:
        inc_error("tests_forbidden")
        return jsonify({"error": "Test çalıştırma devre dışı. ALLOW_ADMIN_TEST_RUN=true yapın."}), 403

    body = request.json or {}
    suite = body.get("suite", "unit")
    extra = body.get("extra", "").strip()
    args = ["pytest", *_suite_to_pytest_args(suite)]

    # Ek argümanları basit regex ile filtrele
    if extra:
        if not re.fullmatch(r"[A-Za-z0-9_\-\s/\.=]*", extra):
            return jsonify({"error": "Geçersiz extra argümanlar"}), 400
        args.extend(shlex.split(extra))

    try:
        proc = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=600,
            cwd=str(_project_root()),
            env=_whitelisted_env(),
        )
        stdout = proc.stdout or ""
        stderr = proc.stderr or ""

        def _clip(s: str, lim: int = 20000) -> str:
            return s if len(s) <= lim else s[:lim] + "\n... (truncated) ...\n"

        result = {
            "exit_code": proc.returncode,
            "suite": suite,
            "cmd": " ".join(args),
            "summary": _parse_summary(stdout + "\n" + stderr),
            "stdout": _clip(stdout),
            "stderr": _clip(stderr),
        }

        user = g.get("user")
        if user:
            create_log(
                user_id=str(user.id),
                username=user.username,
                ip_address=request.remote_addr or "unknown",
                action="admin_tests_run",
                target="/api/admin/tests/run",
                description=f"suite={suite} exit={proc.returncode}",
                status="success" if proc.returncode == 0 else "error",
                user_agent=request.headers.get("User-Agent", ""),
            )

        # Çalıştırma kaydını DB'ye yaz
        try:
            from backend.models.admin_test_run import AdminTestRun, db

            run = AdminTestRun(
                user_id=str(user.id) if user else None,
                username=user.username if user else None,
                suite=suite,
                exit_code=proc.returncode,
                summary_raw=result["summary"]["raw"],
            )
            db.session.add(run)
            db.session.commit()
        except Exception as e:
            logger.exception("Admin test run DB kaydı başarısız")
            inc_error("admin_test_run_db")
            db.session.rollback()

        status = 200 if proc.returncode == 0 else 202
        return jsonify(result), status

    except subprocess.TimeoutExpired:
        inc_error("tests_timeout")
        return jsonify({"error": "Test çalıştırma zaman aşımına uğradı (timeout)."}), 504
    except Exception as e:  # pragma: no cover
        inc_error("tests_exception")
        return jsonify({"error": str(e)}), 500


@admin_tests_bp.get("/status")
@jwt_required_if_not_testing()
@admin_required()
def tests_status():
    """UI'nin toggle durumunu okuyabilmesi için basit durum endpoint'i."""
    user = g.get("user")
    if user:
        create_log(
            user_id=str(user.id),
            username=user.username,
            ip_address=request.remote_addr or "unknown",
            action="admin_tests_status",
            target="/api/admin/tests/status",
            description=f"allowed={_ALLOW}",
            status="success",
            user_agent=request.headers.get("User-Agent", ""),
        )
    return jsonify({"allowed": bool(_ALLOW)}), 200


@admin_tests_bp.get("/history")
@jwt_required_if_not_testing()
@admin_required()
def tests_history():
    """Geçmiş test çalıştırma kayıtlarını döner."""
    from backend.models.admin_test_run import AdminTestRun

    q = (
        AdminTestRun.query.order_by(AdminTestRun.created_at.desc()).limit(20).all()
    )
    user = g.get("user")
    if user:
        create_log(
            user_id=str(user.id),
            username=user.username,
            ip_address=request.remote_addr or "unknown",
            action="admin_tests_history",
            target="/api/admin/tests/history",
            description="list last 20 runs",
            status="success",
            user_agent=request.headers.get("User-Agent", ""),
        )
    return jsonify([r.to_dict() for r in q]), 200
