import asyncio
import json

from app.schemas.component_schema import UIDocument
from app.services import react_export, vision_ai
from app.services.codegen_service import render_site
from tests.test_codegen import parse

BOX = {"x": 0, "y": 0, "w": 1, "h": 1}

# A real reply from the vision model for a 3-screen food-delivery sketch (compact format)
REPLY = {"s": [
    ["Home", [["row", "", [["icon", "location"], ["t", "Select Area"], ["icon", "chevron"], ["ibtn", "bell"]]],
              ["search", "Search dishes"], ["carousel", "Featured"],
              ["row", "", [["img", "Pizza"], ["img", "Burger"], ["img", "Sushi"], ["img", "Salad"]]],
              ["row", "", [["t", "Popular near you"], ["t", "See all"]]],
              ["list", "", [["row", "", [["img", "Dish"], ["col", "", [["t", "Spice Garden"], ["row", "", [["icon", "star"], ["t", "4.5"]]]]], ["ibtn", "heart"]]]]],
              ["bnav", "home|search|bag|user"]]],
    ["Restaurant", [["row", "", [["ibtn", "back"], ["t", "Spice Garden"], ["ibtn", "heart"]]],
                    ["row", "", [["t", "Menu"], ["t", "Reviews"], ["t", "Info"]]],
                    ["list", "", [["row", "", [["img", "Dish"], ["col", "", [["t", "Paneer Tikka"], ["t", "₹ 249"]]], ["ibtn", "plus"]]]]],
                    ["row", "", [["ibtn", "cart"], ["t", "View cart"], ["ibtn", "arrow"]]]]],
    ["Tracking", [["row", "", [["ibtn", "back"], ["t", "Track order"]]], ["map", "Route"],
                  ["row", "", [["ibtn", "truck"], ["t", "On the way"]]], ["progress", "75"],
                  ["timeline", "Placed|Packed|On the way|Delivered"],
                  ["row", "", [["row", "", [["ibtn", "phone"], ["t", "Call"]]], ["row", "", [["ibtn", "chat"], ["t", "Chat"]]]]],
                  ["chart", "pie|Food|Delivery|Tax"]]],
]}


def detected(n=3, with_link=True):
    screens = [{"id": f"screen_{i}", "name": f"S{i}", "root": {"id": f"r{i}", "type": "container", "bbox": BOX, "children": [
        {"id": f"b{i}", "type": "button", "bbox": BOX, "props": {"text": "View cart"}}]}} for i in range(n)]
    a = 1 if n > 2 else 0
    links = [{"fromScreen": f"screen_{a}", "fromComponent": f"b{a}", "toScreen": f"screen_{a + 1}"}] if with_link else []
    return UIDocument.model_validate({"name": "Food", "screens": screens, "links": links})


def types(doc):
    return [c.type for s in doc.screens for c in s.root.walk()]


def test_reply_becomes_a_rich_valid_document():
    doc = vision_ai.to_document(REPLY, detected())
    assert [s.name for s in doc.screens] == ["Home", "Restaurant", "Tracking"]
    assert [s.id for s in doc.screens] == ["screen_0", "screen_1", "screen_2"]  # detector's ids kept
    for kind in ("search", "carousel", "bottomnav", "tabs", "map", "progress", "timeline", "chart", "rating", "price", "listitem"):
        assert kind in types(doc), kind


def test_tidy_rules():
    doc = vision_ai.to_document(REPLY, detected())
    home, rest, track = doc.screens
    tiles = next(c for c in home.root.walk() if c.layout == "row" and c.children and c.children[0].type == "container")
    assert [k.children[1].props.text for k in tiles.children] == ["Pizza", "Burger", "Sushi", "Salad"]
    assert any(c.type == "link" and c.props.text == "See all" for c in home.root.walk())
    assert next(c for c in home.root.walk() if c.type == "rating").props.value == 4.5
    assert next(c for c in rest.root.walk() if c.type == "tabs").props.options == ["Menu", "Reviews", "Info"]
    assert any(c.type == "heading" and c.props.text == "Spice Garden" for c in rest.root.walk())
    cart = next(c for c in rest.root.walk() if c.type == "button")
    assert (cart.props.text, cart.props.icon) == ("View cart", "cart")
    assert [(c.props.text, c.props.icon) for c in track.root.walk() if c.type == "button"] == [("Call", "phone"), ("Chat", "chat")]
    assert next(c for c in track.root.walk() if c.type == "timeline").props.value == 2  # 75% of 4 steps
    assert next(c for c in track.root.walk() if c.props.icon == "truck").type == "icon"
    assert next(c for c in track.root.walk() if c.type == "chart").props.variant == "pie"


def test_drawn_arrow_moves_to_the_matching_button():
    doc = vision_ai.to_document(REPLY, detected())
    cart = next(c for c in doc.screens[1].root.walk() if c.type == "button")
    assert [(l.fromScreen, l.fromComponent, l.toScreen) for l in doc.links] == [("screen_1", cart.id, "screen_2")]


def test_screen_count_mismatch_drops_links_but_keeps_screens():
    doc = vision_ai.to_document(REPLY, detected(2))
    assert len(doc.screens) == 3 and doc.links == []


def test_bad_replies_give_none():
    for bad in ({}, {"s": []}, {"s": [["Only a name"]]}, [], "nope"):
        assert vision_ai.to_document(bad, detected()) is None


def test_pages_render_well_formed_and_export_to_jsx():
    doc = vision_ai.to_document(REPLY, detected())
    for html in render_site(doc).values():
        tags = parse(html)
        icon_only = [a for t, a in tags if t in ("a", "button") and "rounded-full" in a.get("class", "") and "h-10" in a.get("class", "")]
        assert all(a.get("aria-label") for a in icon_only)  # icon buttons have names
    files = react_export.build_project(doc)
    jsx = "".join(v for k, v in files.items() if k.endswith(".jsx"))
    for raw in (' class="', "stroke-width", "stroke-dasharray", ' for="'):
        assert raw not in jsx, raw


def test_describe_falls_back_to_none_when_the_model_fails():
    class Broken:
        class chat:
            class completions:
                @staticmethod
                async def create(**_):
                    raise RuntimeError("429 rate limited")

    assert asyncio.run(vision_ai.describe(b"img", detected(), client=Broken())) is None


def test_describe_parses_a_fenced_reply():
    class Fake:
        class chat:
            class completions:
                @staticmethod
                async def create(**_):
                    msg = type("M", (), {"content": "```json\n" + json.dumps(REPLY) + "\n```"})
                    return type("R", (), {"choices": [type("C", (), {"message": msg})]})

    doc = asyncio.run(vision_ai.describe(b"img", detected(), client=Fake()))
    assert doc is not None and len(doc.screens) == 3
