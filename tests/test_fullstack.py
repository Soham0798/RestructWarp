import importlib.util
import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from app.schemas.component_schema import UIDocument
from app.services.fullstack_service import build_fullstack

EXAMPLE = Path(__file__).resolve().parents[1] / "shared" / "examples" / "login_flow.json"


def files():
    return build_fullstack(UIDocument.model_validate(json.loads(EXAMPLE.read_text())))


def load_backend(tmp_path, monkeypatch):
    path = tmp_path / "main.py"
    path.write_text(files()["backend/main.py"])
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    spec = importlib.util.spec_from_file_location("generated_main", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["generated_main"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_export_has_frontend_and_backend():
    assert {"frontend/index.html", "frontend/dashboard.html", "backend/main.py",
            "backend/requirements.txt"} <= set(files())


def test_form_is_wired_to_its_endpoint():
    html = files()["frontend/index.html"]
    assert 'data-endpoint="/api/login"' in html
    assert 'data-field="email"' in html and 'data-field="password"' in html


def test_generated_backend_runs_and_hides_passwords(tmp_path, monkeypatch):
    mod = load_backend(tmp_path, monkeypatch)
    client = TestClient(mod.app)
    created = client.post("/api/login", json={"email": "a@b.com", "password": "secret123"})
    assert created.status_code == 201
    assert "password" not in created.json() and created.json()["email"] == "a@b.com"
    assert client.post("/api/login", json={"email": "not-an-email", "password": "x"}).status_code == 422
    assert [r["email"] for r in client.get("/api/login").json()] == ["a@b.com"]
    row = mod.SessionLocal().query(mod.LoginSubmission).one()
    assert row.password_hash != "secret123" and ":" in row.password_hash


def test_screens_without_forms_get_no_backend():
    d = json.loads(EXAMPLE.read_text())
    del d["screens"][0]["root"]["children"][2]["form"]
    assert "backend/main.py" not in build_fullstack(UIDocument.model_validate(d))
