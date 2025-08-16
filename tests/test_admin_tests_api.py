from types import SimpleNamespace

from backend import create_app
import importlib


def test_run_tests(monkeypatch):
    monkeypatch.setenv("FLASK_ENV", "testing")
    monkeypatch.setenv("ALLOW_ADMIN_TEST_RUN", "true")
    # admin_required bypass
    monkeypatch.setattr("backend.auth.middlewares.admin_required", lambda: (lambda f: f))

    # Ortam değişkeni değiştikten sonra modülü yeniden yükle
    import backend.api.admin.tests as admin_tests_module
    importlib.reload(admin_tests_module)

    # subprocess.run'ı sahte sonuç dönecek şekilde patchle
    def fake_run(args, capture_output, text, timeout, env):
        return SimpleNamespace(returncode=0, stdout="=== 1 passed in 0.01s ===", stderr="")

    monkeypatch.setattr("subprocess.run", fake_run)

    app = create_app()
    client = app.test_client()

    resp = client.post("/api/admin/tests/run", json={"suite": "unit"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["summary"]["passed"] == 1
    assert data["exit_code"] == 0
