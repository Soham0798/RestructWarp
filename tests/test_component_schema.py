import copy
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.schemas.component_schema import UIDocument

EXAMPLE = Path(__file__).resolve().parents[1] / "shared" / "examples" / "login_flow.json"


@pytest.fixture
def doc():
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


def login_btn(doc):
    return doc["screens"][0]["root"]["children"][2]["children"][2]


def test_example_is_valid(doc):
    ui = UIDocument.model_validate(doc)
    assert len(ui.screens) == 2
    assert ui.links[0].toScreen == "screen_dashboard"


def test_unknown_type_rejected(doc):
    login_btn(doc)["type"] = "spaceship"
    with pytest.raises(ValidationError):
        UIDocument.model_validate(doc)


def test_unknown_key_rejected(doc):
    login_btn(doc)["colour"] = "blue"
    with pytest.raises(ValidationError):
        UIDocument.model_validate(doc)


def test_button_cannot_have_children(doc):
    login_btn(doc)["children"] = [copy.deepcopy(login_btn(doc)) | {"id": "inner"}]
    with pytest.raises(ValidationError, match="cannot have children"):
        UIDocument.model_validate(doc)


def test_bbox_must_be_fraction(doc):
    login_btn(doc)["bbox"]["w"] = 340
    with pytest.raises(ValidationError):
        UIDocument.model_validate(doc)


def test_duplicate_id_rejected(doc):
    login_btn(doc)["id"] = "email_input"
    with pytest.raises(ValidationError, match="duplicate component id"):
        UIDocument.model_validate(doc)


def test_link_to_missing_screen_rejected(doc):
    doc["links"][0]["toScreen"] = "screen_settings"
    with pytest.raises(ValidationError, match="unknown screen"):
        UIDocument.model_validate(doc)


def test_link_from_component_on_other_screen_rejected(doc):
    doc["links"][0]["fromComponent"] = "dash_title"
    with pytest.raises(ValidationError, match="not on screen"):
        UIDocument.model_validate(doc)
