import asyncio
import json
from pathlib import Path

import pytest

from app.schemas.component_schema import UIDocument
from app.services import a11y_service, llm_service
from app.services.codegen_service import render_site

EXAMPLE = Path(__file__).resolve().parents[1] / "shared" / "examples" / "login_flow.json"
BAD = ('<!doctype html><html><head></head><body><img src="x.png"><select name="city"></select>'
       '<button></button></body></html>')

try:
    a11y_service.audit("<!doctype html><html lang='en'><head><title>t</title></head><body></body></html>")
except a11y_service.AuditUnavailable:
    pytest.skip("axe-core not installed (npm install in backend/a11y)", allow_module_level=True)


def test_generated_pages_score_full_marks():
    for name, html in render_site(UIDocument.model_validate(json.loads(EXAMPLE.read_text()))).items():
        result = a11y_service.audit(html)
        assert result["score"] == 100, (name, result["violations"])


def test_bad_page_loses_points():
    result = a11y_service.audit(BAD)
    ids = {v["id"] for v in result["violations"]}
    assert {"image-alt", "button-name", "html-has-lang", "document-title"} <= ids
    assert result["score"] < 60


def test_rules_fix_the_bad_page_without_llm(monkeypatch):
    monkeypatch.setattr(llm_service.settings, "LLM_API_KEY", "")
    out = asyncio.run(a11y_service.improve(BAD))
    assert out["how"] == "rules"
    assert out["after"] > out["before"] + 30
    assert out["after"] == 100, out["violations"]


def test_clean_page_is_left_alone(monkeypatch):
    monkeypatch.setattr(llm_service.settings, "LLM_API_KEY", "")
    html = render_site(UIDocument.model_validate(json.loads(EXAMPLE.read_text())))["index.html"]
    out = asyncio.run(a11y_service.improve(html))
    assert out["how"] == "none" and out["html"] == html
