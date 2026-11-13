"""Step 25: let the LLM fix vision mistakes and turn notes into styles, then re-validate.

Without an LLM the document is kept as detected and notes are resolved by STYLE_RULES,
so the pipeline still works offline.
"""
import json
from typing import Optional

from openai import AsyncOpenAI
from pydantic import ValidationError

from app.schemas.component_schema import UIDocument
from app.services import llm_service

# Handwritten note word -> style hint (Tailwind-flavoured values the code generators understand)
STYLE_RULES = {
    "blue": {"color": "blue"}, "red": {"color": "red"}, "green": {"color": "green"},
    "black": {"color": "black"}, "dark": {"theme": "dark"}, "light": {"theme": "light"},
    "big": {"size": "lg"}, "large": {"size": "lg"}, "small": {"size": "sm"},
    "bold": {"weight": "bold"}, "rounded": {"radius": "full"}, "round": {"radius": "full"},
    "sticky": {"position": "sticky"}, "fixed": {"position": "sticky"},
    "center": {"align": "center"}, "centre": {"align": "center"}, "left": {"align": "left"}, "right": {"align": "right"},
    "shadow": {"shadow": "md"}, "hidden": {"display": "hidden"},
}
# The only values the code generators act on, per key (colors: any Tailwind color name)
ALLOWED = {}
for _style in STYLE_RULES.values():
    for _k, _v in _style.items():
        ALLOWED.setdefault(_k, set()).add(_v)

SYSTEM = """You correct UI component trees produced by a sketch detector.
Return ONLY a JSON object in exactly the same format as the input. Rules:
- Keep every id, screen and link; never invent screens or links.
- Allowed types: navbar, heading, text, button, input, textarea, image, checkbox, dropdown, card, container, footer.
  Only navbar, card, container, footer may have children or a layout.
- Fix obvious mistakes: e.g. a 'button' whose text is a sentence is 'text'; a 'text' reading 'Submit' is a 'button'.
- Fill props sensibly (button text, input placeholder and ariaLabel, image alt, heading level 1-6).
- For each styleHints.notes entry, set styleHints.styles using only these keys and values:
  color: a Tailwind color name (blue, red, green, ...); """ + "; ".join(
    f"{k}: {'/'.join(sorted(v))}" for k, v in sorted(ALLOWED.items()) if k != "color") + """
  (e.g. "blue, rounded" -> {"color": "blue", "radius": "full"}).
- Keep bbox values unchanged."""


def normalize_styles(doc: UIDocument) -> UIDocument:
    """Map an LLM's own words onto the values the generators know ("rounded" -> "full"); drop the rest."""
    for screen in doc.screens:
        for comp in screen.root.walk():
            if not comp.styleHints:
                continue
            clean = {}
            for k, v in comp.styleHints.styles.items():
                v = str(v).strip().lower()
                if k == "color" and v.isalpha():
                    clean[k] = v
                elif v in ALLOWED.get(k, ()):
                    clean[k] = v
                elif k in STYLE_RULES.get(v, {}):
                    clean[k] = STYLE_RULES[v][k]
            comp.styleHints.styles = clean
    return doc


def apply_style_rules(doc: UIDocument) -> UIDocument:
    for screen in doc.screens:
        for comp in screen.root.walk():
            if comp.styleHints:
                for note in comp.styleHints.notes:
                    for word in note.lower().replace(",", " ").split():
                        for k, v in STYLE_RULES.get(word, {}).items():
                            comp.styleHints.styles.setdefault(k, v)
    return doc


def _same_skeleton(a: UIDocument, b: UIDocument) -> bool:
    ids = lambda d: {s.id: {c.id for c in s.root.walk()} for s in d.screens}
    links = lambda d: [(l.fromScreen, l.fromComponent, l.toScreen) for l in d.links]
    return ids(a) == ids(b) and links(a) == links(b)


async def refine(doc: UIDocument, client: Optional[AsyncOpenAI] = None) -> tuple[UIDocument, str]:
    """Returns (document, how) where how is 'llm' or 'rules'."""
    messages = [{"role": "system", "content": SYSTEM},
                {"role": "user", "content": doc.model_dump_json(exclude_none=True)}]
    for _ in range(2):  # one retry, telling the model what was wrong
        try:
            reply = await llm_service.chat(messages, json_mode=True, client=client)
        except llm_service.LLMUnavailable:
            break
        try:
            fixed = UIDocument.model_validate(llm_service.extract_json(reply))
            if _same_skeleton(doc, fixed):
                return apply_style_rules(normalize_styles(fixed)), "llm"
            problem = "You changed ids, screens or links. Keep them exactly as given."
        except (ValueError, ValidationError) as e:
            problem = f"Invalid output: {str(e)[:500]}"
        messages += [{"role": "assistant", "content": reply}, {"role": "user", "content": problem}]
    return apply_style_rules(doc.model_copy(deep=True)), "rules"
