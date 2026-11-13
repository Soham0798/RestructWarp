"""The whole vision pipeline in one call: photo bytes -> UIDocument (Steps 17-22)."""
from app.schemas.component_schema import UIDocument
from app.services.vision import detect, layout, ocr, preprocess


def analyze(image_bytes: bytes, name: str = "Sketch") -> UIDocument:
    cleaned = preprocess.clean(preprocess.load_image(image_bytes))
    dets = detect.detect(cleaned.image)
    try:
        ocr.read_text(cleaned.plain, dets)
    except ocr.OCRUnavailable:
        pass  # layout still works; the LLM step fills in default labels
    h, w = cleaned.image.shape[:2]
    return layout.build_document(dets, w, h, name=name)
