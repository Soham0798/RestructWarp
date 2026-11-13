from app.services.vision.ocr import assign_text
from app.services.vision.types import Detection


def test_lines_go_to_the_smallest_box_holding_them():
    card = Detection("card", 0, 0, 400, 300)
    button = Detection("button", 20, 200, 200, 240)
    assign_text([card, button], [("Login", 0.9, (60, 210, 140, 230)), ("Welcome", 0.9, (20, 20, 150, 50))])
    assert button.text == "Login" and card.text == "Welcome"


def test_checkbox_caption_beside_the_box():
    box = Detection("checkbox", 10, 10, 26, 26)
    assign_text([box], [("Remember me", 0.9, (34, 8, 140, 28))])
    assert box.text == "Remember me"


def test_two_lines_join_in_reading_order():
    text = Detection("text", 0, 0, 300, 60)
    assign_text([text], [("world", 0.9, (0, 30, 100, 50)), ("hello", 0.9, (0, 5, 100, 25))])
    assert text.text == "hello world"


def test_empty_square_read_as_a_glyph_is_ignored():
    box = Detection("checkbox", 10, 10, 26, 26)
    assign_text([box], [("口", 0.9, (10, 10, 26, 26))])  # OCR reads an empty box as 口
    assert box.text == ""


def test_label_and_note_joined_into_one_line_are_split():
    button = Detection("button", 0, 0, 100, 30)
    note = Detection("note", 110, 5, 160, 25)
    assign_text([button, note], [("Sign up green", 0.9, (10, 5, 160, 25))])
    assert button.text == "Sign up" and note.text == "green"
