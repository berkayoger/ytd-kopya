from __future__ import annotations
import os, re, shlex, subprocess
from flask import Blueprint, jsonify, request, g
from backend.auth.jwt_utils import jwt_required_if_not_testing
from backend.auth.middlewares import admin_required
from backend.utils.logger import create_log
from backend.observability.metrics import inc_error
from backend import limiter

admin_tests_bp = Blueprint("admin_tests", __name__, url_prefix="/api/admin/tests")

# Ortam değişkeni ile kapatılabilir
_ALLOW = os.getenv("ALLOW_ADMIN_TEST_RUN", "false").strip().lower() in {"1", "true", "yes", "on"}


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
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
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

        status = 200 if proc.returncode == 0 else 202
        return jsonify(result), status

    except subprocess.TimeoutExpired:
        inc_error("tests_timeout")
        return jsonify({"error": "Test çalıştırma zaman aşımına uğradı (timeout)."}), 504
    except Exception as e:  # pragma: no cover
        inc_error("tests_exception")
        return jsonify({"error": str(e)}), 500
