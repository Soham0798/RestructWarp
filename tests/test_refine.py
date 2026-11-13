import asyncio
import json
from pathlib import Path

import httpx

from app.schemas.component_schema import UIDocument
from app.services import llm_service, refine_service

EXAMPLE = Path(__file__).resolve().parents[1] / "shared" / "examples" / "login_flow.json"


def doc():
    d = json.loads(EXAMPLE.read_text())
    btn = d["screens"][0]["root"]["children"][2]["children"][2]
    btn["styleHints"] = {"notes": ["blue, rounded"], "styles": {}}
    return UIDocument.model_validate(d)


def fake_llm(*replies):
    """An OpenAI-compatible server that answers with the given texts in order."""
    queue = list(replies)

    def handler(request):
        body = {"id": "x", "object": "chat.completion", "created": 0, "model": "m",
                "choices": [{"index": 0, "finish_reason": "stop",
                             "message": {"role": "assistant", "content": queue.pop(0)}}]}
        return httpx.Response(200, json=body)

    return llm_service.make_client(httpx.AsyncClient(transport=httpx.MockTransport(handler)))


def button(d):
    return next(c for c in d.screens[0].root.walk() if c.id == "login_btn")


def test_extract_json_handles_fences():
    assert llm_service.extract_json('Sure!\n```json\n{"a": 1}\n```') == {"a": 1}


def test_rules_resolve_notes_without_llm(monkeypatch):
    monkeypatch.setattr(llm_service.settings, "LLM_API_KEY", "")
    out, how = asyncio.run(refine_service.refine(doc()))
    assert how == "rules"
    assert button(out).styleHints.styles == {"color": "blue", "radius": "full"}


def test_llm_fix_is_used():
    fixed = doc().model_dump(exclude_none=True)
    fixed["screens"][1]["root"]["children"][1]["props"]["text"] = "Welcome to your dashboard"
    out, how = asyncio.run(refine_service.refine(doc(), client=fake_llm(json.dumps(fixed))))
    assert how == "llm"
    assert out.screens[1].root.children[1].props.text == "Welcome to your dashboard"


def test_bad_llm_output_is_retried_then_falls_back():
    out, how = asyncio.run(refine_service.refine(doc(), client=fake_llm("not json", '{"name": "x"}')))
    assert how == "rules"
    assert button(out).styleHints.styles["color"] == "blue"


def test_llm_may_not_drop_links():
    broken = doc().model_dump(exclude_none=True)
    broken["links"] = []
    _, how = asyncio.run(refine_service.refine(doc(), client=fake_llm(json.dumps(broken), json.dumps(broken))))
    assert how == "rules"


def test_llm_style_words_are_mapped_to_generator_values():
    doc = UIDocument.model_validate(json.loads(EXAMPLE.read_text()))
    btn = next(c for s in doc.screens for c in s.root.walk() if c.styleHints)
    btn.styleHints.styles = {"color": "Blue", "radius": "rounded", "size": "large", "shadow": "glow", "font": "comic"}
    refine_service.normalize_styles(doc)
    assert btn.styleHints.styles == {"color": "blue", "radius": "full", "size": "lg"}
