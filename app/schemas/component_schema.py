"""Pydantic models for the shared component tree (schema v2).

This file is the single source of truth. shared/component.schema.json is
generated from it with:  python -m app.schemas.export_schema
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

SCHEMA_VERSION = "2.0"

ComponentType = Literal[
    "navbar", "heading", "text", "button", "input", "textarea",
    "image", "checkbox", "dropdown", "card", "container", "footer",
    # app-style elements the vision model reads (the detector doesn't know them)
    "icon", "iconbutton", "search", "link", "carousel", "list", "listitem", "tabs", "bottomnav",
    "map", "progress", "timeline", "chart", "table", "rating", "price", "badge", "toggle", "slider",
]

# Only these types may hold other components.
CONTAINER_TYPES = {"navbar", "card", "container", "footer", "list", "listitem"}

FieldType = Literal[
    "text", "email", "password", "number", "textarea", "checkbox", "select", "date",
]


class Strict(BaseModel):
    """Base class: reject unknown keys so typos are caught early."""
    model_config = ConfigDict(extra="forbid")


class BBox(Strict):
    """Position and size as fractions (0-1) of the screen, so image size doesn't matter."""
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)
    w: float = Field(gt=0, le=1)
    h: float = Field(gt=0, le=1)


class Props(Strict):
    """Content and accessibility details. Each type uses only the props it needs."""
    text: Optional[str] = None
    placeholder: Optional[str] = None
    src: Optional[str] = None
    alt: Optional[str] = None
    ariaLabel: Optional[str] = None
    level: Optional[int] = Field(default=None, ge=1, le=6)
    options: Optional[list[str]] = None  # also tabs, nav items, timeline steps, table columns, chart labels
    checked: Optional[bool] = None
    icon: Optional[str] = None           # icon name (icons.py), e.g. "heart"
    value: Optional[float] = None        # progress percent, rating, current timeline step
    variant: Optional[str] = None        # chart kind: pie, donut, bar, line


class StyleHints(Strict):
    """Handwritten notes (F3): raw OCR text, plus the styles the LLM resolved them to."""
    notes: list[str] = []
    styles: dict[str, str] = {}


class FormField(Strict):
    """One field of a form, used to generate the backend (F4)."""
    name: str = Field(pattern=r"^[a-z_][a-z0-9_]*$")
    type: FieldType
    label: Optional[str] = None
    required: bool = False
    componentId: Optional[str] = None


class Form(Strict):
    name: str = Field(pattern=r"^[a-z_][a-z0-9_]*$")
    fields: list[FormField] = Field(min_length=1)


class Component(Strict):
    id: str = Field(min_length=1)
    type: ComponentType
    bbox: BBox
    props: Props = Props()
    layout: Optional[Literal["row", "column", "grid"]] = None
    children: list[Component] = []
    styleHints: Optional[StyleHints] = None
    form: Optional[Form] = None
    confidence: Optional[float] = Field(default=None, ge=0, le=1)

    @model_validator(mode="after")
    def check_type_rules(self) -> Component:
        is_container = self.type in CONTAINER_TYPES
        if self.children and not is_container:
            raise ValueError(f"'{self.type}' ({self.id}) cannot have children")
        if self.layout and not is_container:
            raise ValueError(f"'{self.type}' ({self.id}) cannot have a layout")
        if self.form and self.type not in {"card", "container"}:
            raise ValueError(f"form on '{self.type}' ({self.id}); only card/container can be forms")
        if self.props.level is not None and self.type != "heading":
            raise ValueError(f"'level' is only for headings ({self.id})")
        return self

    def walk(self):
        """Yield this component and every component inside it."""
        yield self
        for child in self.children:
            yield from child.walk()


class Screen(Strict):
    id: str = Field(min_length=1)
    name: str
    root: Component


class Link(Strict):
    """A drawn arrow (F2): clicking `fromComponent` on `fromScreen` opens `toScreen`."""
    fromScreen: str
    fromComponent: str
    toScreen: str
    trigger: Literal["click"] = "click"


class UIDocument(Strict):
    """The whole sketch: one or more screens and the links between them."""
    schemaVersion: Literal["2.0"] = SCHEMA_VERSION
    name: str
    screens: list[Screen] = Field(min_length=1)
    links: list[Link] = []

    @model_validator(mode="after")
    def check_references(self) -> UIDocument:
        screen_ids = [s.id for s in self.screens]
        if len(screen_ids) != len(set(screen_ids)):
            raise ValueError("screen ids must be unique")

        components_by_screen: dict[str, set[str]] = {}
        seen: set[str] = set()
        for screen in self.screens:
            ids = set()
            for comp in screen.root.walk():
                if comp.id in seen:
                    raise ValueError(f"duplicate component id '{comp.id}'")
                seen.add(comp.id)
                ids.add(comp.id)
            components_by_screen[screen.id] = ids

            for comp in screen.root.walk():
                for field in comp.form.fields if comp.form else []:
                    if field.componentId and field.componentId not in ids:
                        raise ValueError(f"form field '{field.name}' points to unknown component '{field.componentId}'")

        for link in self.links:
            if link.fromScreen not in components_by_screen:
                raise ValueError(f"link from unknown screen '{link.fromScreen}'")
            if link.toScreen not in components_by_screen:
                raise ValueError(f"link to unknown screen '{link.toScreen}'")
            if link.fromComponent not in components_by_screen[link.fromScreen]:
                raise ValueError(f"link starts at '{link.fromComponent}', which is not on screen '{link.fromScreen}'")
        return self
