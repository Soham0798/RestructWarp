"""Write shared/component.schema.json from the Pydantic models.

Run from backend/:  python -m app.schemas.export_schema
"""
import json
from pathlib import Path

from app.schemas.component_schema import UIDocument

OUT = Path(__file__).resolve().parents[2] / "shared" / "component.schema.json"

if __name__ == "__main__":
    schema = UIDocument.model_json_schema()
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["title"] = "Sketch2UI component tree v2"
    OUT.write_text(json.dumps(schema, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT}")
