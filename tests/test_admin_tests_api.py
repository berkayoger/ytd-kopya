import importlib
from dataclasses import dataclass

import pytest
from backend import create_app, db


@pytest.fixture()
def admin_client(monkeypatch):
    """Admin JWT ve admin_required kontrolünü test ortamında bypass eden test client."""
    monkeypatch.setenv("FLASK_ENV", "testing")
    # admin_required bypass
    monkeypatch.setattr("backend.auth.middlewares.admin_required", lambda: (lambda f: f))
    # JWT verify bypass (jwt_required_if_not_testing zaten testing'te no-op ama yine de güvence)
    import flask_jwt_extended.view_decorators as vd
    monkeypatch.setattr(vd, "verify_jwt_in_request", lambda *a, **k: None)

    app = create_app()
    app.config["TESTING"] = True
    with app.app_context():
        db.create_all()
    try:
        yield app.test_client()
    finally:
        with app.app_context():
            db.session.remove()
            db.drop_all()


@dataclass
class DummyProc:
    returncode: int = 0
    stdout: str = ""
    stderr: str = ""


def _reload_tests_module(monkeypatch, allow: bool):
    """/api/admin/tests blueprint'inin ALLOW_ADMIN_TEST_RUN değerini alması için modülü yeniden yükle."""
    monkeypatch.setenv("ALLOW_ADMIN_TEST_RUN", "true" if allow else "false")
    # import sırası önemli: önce modülü reload et, sonra app'i import eden testler onu kullanıyor olacak
    import backend.api.admin.tests as admin_tests_module
    importlib.reload(admin_tests_module)


def test_run_tests_success(admin_client, monkeypatch):
    """Mutlu yol: ALLOW_ADMIN_TEST_RUN=true iken, subprocess.run mock'lanır ve
    0 exit code + anlaşılır summary üretir; API 200 döner ve özet parse edilir."""
    _reload_tests_module(monkeypatch, allow=True)

    # subprocess.run'ı sahtele: pytest çıktısının son satırında özet versin
    summary_line = "=== 3 passed, 1 skipped in 0.12s ===\n"
    dummy_out = "collected 4 items\n\n" + summary_line

    def fake_run(args, capture_output, text, timeout, cwd, env):
        assert "pytest" in args[0]
        # suite seçimine göre -k filtrelerinin geldiğini doğrulamamız şart değil
        return DummyProc(returncode=0, stdout=dummy_out, stderr="")

    monkeypatch.setattr("subprocess.run", fake_run)

    r = admin_client.post("/api/admin/tests/run", json={"suite": "unit", "extra": ""})
    assert r.status_code == 200
    body = r.get_json()
    # Komut bilgisini ve özetin parse edildiğini doğrula
    assert body["exit_code"] == 0
    assert "cmd" in body and "pytest" in body["cmd"]
    assert body["summary"]["passed"] == 3
    assert body["summary"]["skipped"] == 1
    assert body["summary"]["failed"] == 0
    assert body["summary"]["errors"] == 0
    # stdout kesilmeden dönüyor (dummy kısa)
    assert "collected 4 items" in body["stdout"]
    assert body["stderr"] == ""


def test_run_tests_forbidden(admin_client, monkeypatch):
    """ALLOW_ADMIN_TEST_RUN=false iken endpoint 403 döner."""
    _reload_tests_module(monkeypatch, allow=False)
    r = admin_client.post("/api/admin/tests/run", json={"suite": "unit"})
    assert r.status_code == 403
    assert "devre dışı" in r.get_json().get("error", "").lower()


def test_run_tests_nonzero_exit_returns_202(admin_client, monkeypatch):
    """pytest exit code !=0 ise API 202 döner ve özet yine parse edilir."""
    _reload_tests_module(monkeypatch, allow=True)

    summary_line = "=== 2 passed, 1 failed in 1.23s ===\n"
    dummy_out = "some output...\n" + summary_line
    dummy_err = "E   AssertionError: boom\n"

    def fake_run(args, capture_output, text, timeout, cwd, env):
        return DummyProc(returncode=1, stdout=dummy_out, stderr=dummy_err)

    monkeypatch.setattr("subprocess.run", fake_run)

    r = admin_client.post("/api/admin/tests/run", json={"suite": "all", "extra": "-k smoke"})
    assert r.status_code == 202
    b = r.get_json()
    assert b["exit_code"] == 1
    assert b["summary"]["passed"] == 2
    assert b["summary"]["failed"] == 1
    assert b["summary"]["errors"] == 0
    assert "AssertionError" in b["stderr"]


def test_status_endpoint(admin_client, monkeypatch):
    """/status endpoint'i ALLOW_ADMIN_TEST_RUN değerini döner."""
    _reload_tests_module(monkeypatch, allow=True)
    r = admin_client.get("/api/admin/tests/status")
    assert r.status_code == 200
    assert r.get_json()["allowed"] is True

    _reload_tests_module(monkeypatch, allow=False)
    r2 = admin_client.get("/api/admin/tests/status")
    assert r2.status_code == 200
    assert r2.get_json()["allowed"] is False


def test_history_endpoint(admin_client, monkeypatch):
    """/history endpoint'i son çalıştırma kayıtlarını döner."""
    _reload_tests_module(monkeypatch, allow=True)

    summary_line = "=== 1 passed in 0.01s ===\n"
    dummy_out = "collected 1 item\n\n" + summary_line

    def fake_run(args, capture_output, text, timeout, cwd, env):
        return DummyProc(returncode=0, stdout=dummy_out, stderr="")

    monkeypatch.setattr("subprocess.run", fake_run)

    r = admin_client.post("/api/admin/tests/run", json={"suite": "unit"})
    assert r.status_code == 200

    hist = admin_client.get("/api/admin/tests/history")
    assert hist.status_code == 200
    body = hist.get_json()
    assert isinstance(body, list) and len(body) == 1
    assert body[0]["suite"] == "unit"
    assert body[0]["exit_code"] == 0


def test_history_filters(admin_client, monkeypatch):
    """/history filtre parametreleriyle çalışır."""
    _reload_tests_module(monkeypatch, allow=True)

    dummy_out = "collected 1 item\n\n=== 1 passed in 0.01s ===\n"

    def fake_run(args, capture_output, text, timeout, cwd, env):
        return DummyProc(returncode=0, stdout=dummy_out, stderr="")

    monkeypatch.setattr("subprocess.run", fake_run)

    # 2 kayıt ekle
    admin_client.post("/api/admin/tests/run", json={"suite": "unit"})
    admin_client.post("/api/admin/tests/run", json={"suite": "smoke"})

    r = admin_client.get("/api/admin/tests/history?suite=unit&exit_code=0")
    data = r.get_json()
    assert all(item["suite"] == "unit" for item in data)
