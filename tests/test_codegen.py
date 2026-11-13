import json
from html.parser import HTMLParser
from pathlib import Path

from app.schemas.component_schema import UIDocument
from app.services.codegen_service import render_site

EXAMPLE = Path(__file__).resolve().parents[1] / "shared" / "examples" / "login_flow.json"
VOID = {"meta", "input", "img", "br", "hr", "link"}


class Checker(HTMLParser):
    """Collects tags and fails on any closing tag that doesn't match the open one."""

    def __init__(self):
        super().__init__()
        self.stack, self.tags = [], []

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))
        if tag not in VOID:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        assert self.stack and self.stack.pop() == tag, f"unbalanced </{tag}>"


def parse(html):
    c = Checker()
    c.feed(html)
    assert c.stack == [], f"unclosed {c.stack}"
    return c.tags


def site():
    return render_site(UIDocument.model_validate(json.loads(EXAMPLE.read_text())))


def test_one_page_per_screen():
    assert set(site()) == {"index.html", "dashboard.html"}


def test_pages_are_well_formed_and_accessible():
    for html in site().values():
        tags = parse(html)
        assert ("html", {"lang": "en"}) in tags
        ids = {a.get("id") for t, a in tags if t in ("input", "textarea", "select")}
        labels = {a.get("for") for t, a in tags if t == "label"}
        assert ids <= labels  # every field has a label
        assert all("alt" in a for t, a in tags if t == "img")


def test_arrow_becomes_link_to_next_page():
    tags = parse(site()["index.html"])
    assert any(t == "a" and a.get("href") == "dashboard.html" for t, a in tags)


def test_form_fields_get_their_types():
    tags = parse(site()["index.html"])
    types = {a["id"]: a["type"] for t, a in tags if t == "input"}
    assert types == {"email_input": "email", "password_input": "password"}
    assert any(t == "form" for t, _ in tags)


def test_note_styles_become_classes():
    html = site()["index.html"]
    assert "bg-blue-600" in html and "rounded-full" in html


def test_text_is_escaped():
    d = json.loads(EXAMPLE.read_text())
    d["screens"][1]["root"]["children"][1]["props"]["text"] = "<script>alert(1)</script>"
    html = render_site(UIDocument.model_validate(d))["dashboard.html"]
    assert "<script>alert" not in html and "&lt;script&gt;" in html


def _three_screens(buttons, in_form=False):
    """Home -> Cart -> Done, with the given button labels on the middle screen and no arrows."""
    box = {"x": 0, "y": 0, "w": 1, "h": 1}
    kids = [{"id": f"b{i}", "type": "button", "bbox": box, "props": {"text": t}} for i, t in enumerate(buttons)]
    if in_form:
        kids = [{"id": "f", "type": "card", "bbox": box, "children": [{"id": "email", "type": "input", "bbox": box}, *kids],
                 "form": {"name": "order", "fields": [{"name": "email", "type": "email", "label": "Email", "componentId": "email"}]}}]
    screen = lambda sid, name, children: {
        "id": sid, "name": name, "root": {"id": f"{sid}_root", "type": "container", "bbox": box, "children": children}}
    doc = {"schemaVersion": "2.0", "name": "shop", "links": [],
           "screens": [screen("s1", "Home", []), screen("s2", "Cart", kids), screen("s3", "Done", [])]}
    return parse(render_site(UIDocument.model_validate(doc))["cart.html"])


def test_unlinked_buttons_still_do_something():
    tags = _three_screens(["Home", "Back", "Continue", "Add to cart", "Hello"])
    hrefs = [a.get("href") for t, a in tags if t == "a"]
    assert hrefs == ["index.html", "index.html", "done.html"]  # by name, back, next
    toasts = [a.get("data-toast") for t, a in tags if t == "button"]
    assert toasts == ["Added to cart", "Hello tapped"]
    assert any(t == "script" for t, _ in tags) and any(a.get("id") == "s2u-toast" for _, a in tags)


def test_unlinked_form_button_submits_then_moves_on():
    tags = _three_screens(["Place order"], in_form=True)
    btn = next(a for t, a in tags if t == "button")
    assert btn["type"] == "submit" and btn["data-next"] == "done.html"
