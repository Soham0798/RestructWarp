import io
import json
import zipfile
from pathlib import Path

from app.schemas.component_schema import UIDocument
from app.services.react_export import build_project, html_to_jsx, to_zip

EXAMPLE = Path(__file__).resolve().parents[1] / "shared" / "examples" / "login_flow.json"


def project():
    return build_project(UIDocument.model_validate(json.loads(EXAMPLE.read_text())))


def test_project_has_a_file_per_screen_and_vite_setup():
    files = project()
    assert {"sketch2ui-app/src/screens/Login.jsx", "sketch2ui-app/src/screens/Dashboard.jsx",
            "sketch2ui-app/src/App.jsx", "sketch2ui-app/package.json"} <= set(files)


def test_jsx_conversion():
    jsx = html_to_jsx('<label for="a" class="x">{hi}</label><input id="a" type="checkbox" checked>'
                      '<a href="dashboard.html" class="b">Go</a>')
    assert 'htmlFor="a"' in jsx and 'className="x"' in jsx and "&#123;hi&#125;" in jsx
    assert jsx.count("/>") == 1 and "defaultChecked" in jsx and 'href="#/dashboard"' in jsx


def test_login_screen_links_to_dashboard_route():
    files = project()
    assert 'href="#/dashboard"' in files["sketch2ui-app/src/screens/Login.jsx"]
    assert '"dashboard": Dashboard' in files["sketch2ui-app/src/App.jsx"]


def test_no_raw_html_attributes_left_in_jsx():
    for path, text in project().items():
        if path.endswith(".jsx"):
            assert ' class="' not in text and ' for="' not in text


def test_zip_round_trip():
    files = project()
    with zipfile.ZipFile(io.BytesIO(to_zip(files))) as z:
        assert set(z.namelist()) == set(files)
