from app.services.vision import notes
from app.services.vision.types import Detection


def test_note_goes_to_the_element_on_its_row():
    button = Detection("button", 0, 100, 300, 130)
    image = Detection("image", 0, 140, 300, 230)  # just below: nearly as close to the note
    note = Detection("note", 308, 112, 360, 141)
    assert notes.nearest(note, [button, image]) is button


def test_far_note_is_ignored():
    button = Detection("button", 0, 0, 100, 30)
    assert notes.nearest(Detection("note", 400, 0, 450, 30), [button]) is None
