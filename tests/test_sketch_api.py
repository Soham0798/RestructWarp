import io
import json
import uuid
import zipfile
from pathlib import Path

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routers import sketch as sketch_router
from app.schemas.component_schema import UIDocument
from app.services import llm_service, pipeline

EXAMPLE = Path(__file__).resolve().parents[1] / "shared" / "examples" / "login_flow.json"
PNG = cv2.imencode(".png", np.full((60, 80, 3), 255, np.uint8))[1].tobytes()


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setattr(sketch_router, "UPLOADS", tmp_path / "uploads")
    # no trained detector or LLM in tests: the pipeline returns the example document
    monkeypatch.setattr(pipeline, "analyze", lambda data, name: UIDocument.model_validate_json(EXAMPLE.read_text()))
    monkeypatch.setattr(llm_service.settings, "LLM_API_KEY", "")
    with TestClient(app) as c:
        yield c


def login(client):
    user = {"email": f"u{uuid.uuid4().hex[:8]}@example.com", "password": "password123"}
    client.post("/auth/register", json=user)
    token = client.post("/auth/login", json=user).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def upload(client, headers, data=PNG, kind="image/png"):
    pid = client.post("/projects", json={"name": "Shop app"}, headers=headers).json()["id"]
    return client.post("/sketch/analyze", data={"project_id": pid},
                       files={"file": ("sketch.png", data, kind)}, headers=headers)


def test_full_flow(client):
    h = login(client)
    res = upload(client, h)
    assert res.status_code == 201 and res.json()["refined_by"] == "rules"
    sid = res.json()["sketch_id"]

    gen = client.post(f"/sketch/{sid}/generate", headers=h).json()
    assert set(gen["pages"]) == {"index.html", "dashboard.html"}

    preview = client.get(gen["preview_url"].replace("http://testserver", ""))  # no login needed (QR on a phone)
    assert preview.status_code == 200 and "<form" in preview.text

    for target, expected in [("html", "index.html"), ("react", "sketch2ui-app/src/App.jsx"),
                             ("fullstack", "backend/main.py")]:
        z = client.get(f"/sketch/{sid}/export?target={target}", headers=h)
        assert expected in zipfile.ZipFile(io.BytesIO(z.content)).namelist()


def test_edit_json_is_validated(client):
    h = login(client)
    sid = upload(client, h).json()["sketch_id"]
    doc = client.get(f"/sketch/{sid}", headers=h).json()
    doc["name"] = "Renamed"
    assert client.put(f"/sketch/{sid}/json", json=doc, headers=h).status_code == 200
    doc["screens"][0]["root"]["type"] = "slider"
    assert client.put(f"/sketch/{sid}/json", json=doc, headers=h).status_code == 422


def test_rejects_wrong_file_type(client):
    assert upload(client, login(client), data=b"%PDF", kind="application/pdf").status_code == 415


def test_other_users_cannot_see_my_sketch(client):
    sid = upload(client, login(client)).json()["sketch_id"]
    assert client.get(f"/sketch/{sid}", headers=login(client)).status_code == 404


def test_requires_login(client):
    assert client.post("/projects", json={"name": "x"}).status_code == 401


def test_unknown_preview_is_404(client):
    assert client.get("/preview/nope/index.html").status_code == 404
