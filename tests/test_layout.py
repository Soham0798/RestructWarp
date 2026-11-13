import random

from app.services.vision.layout import build_document, find_screens
from app.services.vision.types import Detection
from tests.test_synth import synth


def as_detections(sk):
    dets = [Detection(c, x1, y1, x2, y2) for c, x1, y1, x2, y2 in sk.boxes]
    for d in dets:  # stand in for OCR
        d.text = {"button": "Login", "input": "Email", "heading": "Welcome", "note": "blue"}.get(d.cls, "")
    return dets


def test_synthetic_sketches_become_valid_documents():
    rng = random.Random(21)
    linked = noted = 0
    for _ in range(25):
        sk = synth.make_sketch(rng)
        h, w = sk.img.shape[:2]
        doc = build_document(as_detections(sk), w, h)  # validates against the schema
        n_frames = sum(1 for b in sk.boxes if b[0] == "container")
        assert len(doc.screens) == n_frames
        linked += len(doc.links)
        noted += sum(1 for s in doc.screens for c in s.root.walk() if c.styleHints)
    assert linked > 0 and noted > 0


def test_arrow_links_button_to_next_screen():
    dets = [
        Detection("container", 0, 0, 300, 600), Detection("container", 500, 0, 800, 600),
        Detection("button", 20, 100, 200, 140, text="Login"),
        Detection("heading", 520, 20, 700, 60, text="Dashboard"),
        Detection("arrow", 196, 90, 506, 150),
    ]
    doc = build_document(dets, 900, 700)
    assert [(l.fromScreen, l.toScreen) for l in doc.links] == [("screen_1", "screen_2")]
    start = doc.links[0].fromComponent
    assert next(c for c in doc.screens[0].root.walk() if c.id == start).type == "button"


def test_note_attaches_to_nearest_element():
    dets = [
        Detection("container", 0, 0, 400, 600),
        Detection("button", 20, 100, 200, 140, text="Login"),
        Detection("input", 20, 200, 200, 240, text="Email"),
        Detection("note", 210, 105, 260, 135, text="blue"),
    ]
    doc = build_document(dets, 500, 700)
    btn = next(c for c in doc.screens[0].root.walk() if c.type == "button")
    assert btn.styleHints.notes == ["blue"]


def test_card_with_inputs_and_button_becomes_form():
    dets = [
        Detection("container", 0, 0, 400, 600),
        Detection("card", 20, 50, 380, 400),
        Detection("input", 40, 80, 360, 120, text="Email"),
        Detection("input", 40, 140, 360, 180, text="Password"),
        Detection("button", 40, 220, 360, 260, text="Login"),
    ]
    doc = build_document(dets, 500, 700)
    card = next(c for c in doc.screens[0].root.walk() if c.type == "card")
    assert [(f.name, f.type) for f in card.form.fields] == [("email", "email"), ("password", "password")]


def test_photo_without_frame_is_one_screen():
    assert len(find_screens([Detection("button", 10, 10, 50, 30)], 640, 480)) == 1


def test_side_by_side_children_are_a_row():
    dets = [Detection("container", 0, 0, 600, 400), Detection("navbar", 10, 10, 590, 80),
            Detection("image", 20, 20, 70, 70), Detection("button", 400, 25, 580, 65, text="Menu")]
    doc = build_document(dets, 700, 500)
    nav = next(c for c in doc.screens[0].root.walk() if c.type == "navbar")
    assert nav.layout == "row" and [c.type for c in nav.children] == ["image", "button"]
