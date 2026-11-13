import importlib.util
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("synth", ROOT / "ml" / "synth_sketches.py")
synth = importlib.util.module_from_spec(spec)
sys.modules["synth"] = synth
spec.loader.exec_module(synth)


def test_classes_match_schema_types_plus_arrow_and_note():
    classes = json.loads((ROOT / "shared" / "detector_classes.json").read_text())
    schema = json.loads((ROOT / "shared" / "component.schema.json").read_text())
    types = set(schema["$defs"]["Component"]["properties"]["type"]["enum"])
    # every detector class is a schema type; the schema also has vision-model-only types (icons, maps, charts...)
    assert set(classes) - {"arrow", "note"} <= types


def test_labels_are_valid_yolo():
    rng = random.Random(1)
    seen = set()
    for _ in range(30):
        sk = synth.make_sketch(rng)
        h, w = sk.img.shape[:2]
        for line in synth.to_yolo(sk.boxes, w, h):
            cid, *vals = line.split()
            seen.add(synth.CLASSES[int(cid)])
            assert all(0 <= float(v) <= 1 for v in vals)
    assert {"container", "button", "arrow", "note"} <= seen  # multi-screen + notes really appear
