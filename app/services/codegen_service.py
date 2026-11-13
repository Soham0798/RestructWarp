"""Step 26/28: UIDocument -> HTML + Tailwind, one page per screen, arrows as real links.

Templates, not free-form LLM text: the same JSON always gives the same, valid, accessible HTML.
Buttons with no drawn arrow still do something: their label picks a screen, Back/Next, or a toast.
"""
import re
from html import escape

from app.schemas.component_schema import CONTAINER_TYPES, Component, Screen, UIDocument
from app.services import app_elements, icons

TAILWIND = """<link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  <script src="https://cdn.tailwindcss.com"></script>
  <script>tailwind.config = { theme: { extend: { fontFamily: { sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"] } } } };</script>"""
IMAGE_PLACEHOLDER = ("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 400 200'>"
                     "<defs><linearGradient id='g' x1='0' y1='0' x2='1' y2='1'><stop offset='0' stop-color='%23e0e7ff'/>"
                     "<stop offset='1' stop-color='%23fce7f3'/></linearGradient></defs>"
                     "<rect width='400' height='200' fill='url(%23g)'/>"
                     "<path d='M168 128l22-28 16 19 11-13 25 22z' fill='%23a5b4fc'/>"
                     "<circle cx='224' cy='86' r='8' fill='%23a5b4fc'/></svg>")
BODY_CLASS = "min-h-screen bg-gradient-to-b from-slate-50 to-indigo-50 font-sans text-slate-900 antialiased"
MAIN_CLASS = "mx-auto flex min-h-screen max-w-md flex-col gap-5 px-5 py-6"

FIELD = ("w-full rounded-xl border-0 bg-white px-4 py-2.5 text-sm shadow-sm ring-1 ring-inset ring-slate-200 "
         "placeholder:text-slate-400 transition focus:outline-none focus:ring-2 focus:ring-indigo-500")
BASE = {
    "navbar": "flex items-center justify-between gap-4 rounded-2xl bg-white/80 px-4 py-3 shadow-sm "
              "ring-1 ring-slate-900/5 backdrop-blur",
    "heading": "font-semibold tracking-tight text-slate-900",
    "text": "text-slate-600 leading-relaxed",
    "button": "inline-flex items-center justify-center gap-2 rounded-xl px-5 py-2.5 text-sm font-semibold shadow-sm "
              "transition hover:shadow-md active:scale-95 focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2",
    "input": FIELD,
    "textarea": f"{FIELD} min-h-28",
    "dropdown": FIELD,
    "image": "w-full h-auto rounded-2xl object-cover ring-1 ring-slate-900/5",
    "card": "rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-900/5 transition hover:shadow-md",
    "container": "",
    "footer": "mt-auto border-t border-slate-200 pt-4 text-center text-xs text-slate-500",
}
ACCENT = "bg-indigo-600 text-white hover:bg-indigo-500 focus-visible:ring-indigo-500"
SECONDARY = "bg-white text-slate-700 ring-1 ring-slate-200 hover:bg-slate-50 focus-visible:ring-slate-400"

# What a button with no drawn arrow does, guessed from its label
BACK_WORDS = ("back", "cancel", "close", "previous", "prev")
NEXT_WORDS = ("next", "continue", "login", "log in", "sign in", "sign up", "signup", "register", "get started",
              "start", "proceed", "go", "submit", "done", "finish", "checkout", "check out", "pay", "confirm")
TOASTS = (
    (("cart", "buy", "add"), "Added to cart"),
    (("like", "favourite", "favorite", "heart", "wishlist"), "Added to favourites"),
    (("share",), "Link copied"),
    (("delete", "remove"), "Removed"),
    (("save", "update", "apply"), "Saved"),
    (("search", "find", "filter"), "Searching…"),
    (("send", "message", "contact"), "Message sent"),
    (("download",), "Download started"),
)

# Toasts for unlinked buttons and a friendly finish for forms (forms wired to a real API are left alone)
RUNTIME = """<div id="s2u-toast" role="status" aria-live="polite" class="pointer-events-none fixed inset-x-0 bottom-6 z-50 flex justify-center px-4"></div>
<script>
// Sketch2UI: what buttons without a drawn arrow do in this prototype
(() => {
  const go = (href) => (window.__sketch2uiGo ? window.__sketch2uiGo(href) : (location.href = href));
  const box = document.getElementById("s2u-toast");
  let timer;
  const toast = (msg) => {
    const el = document.createElement("div");
    el.className = "rounded-full bg-slate-900/90 px-4 py-2 text-sm font-medium text-white shadow-lg transition duration-300 opacity-0 translate-y-2";
    el.textContent = msg;
    box.replaceChildren(el);
    requestAnimationFrame(() => requestAnimationFrame(() => el.classList.remove("opacity-0", "translate-y-2")));
    clearTimeout(timer);
    timer = setTimeout(() => el.classList.add("opacity-0", "translate-y-2"), 1800);
  };
  document.addEventListener("click", (e) => {
    const b = e.target.closest("[data-toast]");
    if (b) toast(b.dataset.toast);
    const fav = e.target.closest("[data-fav]");
    if (fav) {
      const on = fav.getAttribute("aria-pressed") !== "true";
      fav.setAttribute("aria-pressed", on);
      fav.classList.toggle("text-rose-500", on);
      fav.querySelector("svg").setAttribute("fill", on ? "currentColor" : "none");
      toast(on ? "Added to favourites" : "Removed from favourites");
    }
    const tab = e.target.closest("[role=tab]");
    if (tab) tab.parentElement.querySelectorAll("[role=tab]").forEach((t) => {
      const on = t === tab;
      t.setAttribute("aria-selected", on);
      ["text-indigo-600", "border-indigo-600"].forEach((c) => t.classList.toggle(c, on));
      ["text-slate-500", "border-transparent"].forEach((c) => t.classList.toggle(c, !on));
    });
  });
  document.addEventListener("submit", (e) => {
    if (e.target.dataset.endpoint) return;
    e.preventDefault();
    toast("Done!");
    const next = e.submitter && e.submitter.dataset.next;
    if (next) setTimeout(() => go(next), 700);
  });
})();
</script>"""
HEADING_SIZE = {1: "text-3xl", 2: "text-2xl", 3: "text-xl", 4: "text-lg", 5: "text-base", 6: "text-sm"}
FILLED = ("button",)  # colour hints fill these; elsewhere they colour the text


def style_classes(comp: Component) -> list[str]:
    """Turn styleHints.styles (F3) into Tailwind classes."""
    s = comp.styleHints.styles if comp.styleHints else {}
    out = []
    if c := s.get("color"):
        out += ([f"bg-{c}-600", f"hover:bg-{c}-500", "text-white", f"focus-visible:ring-{c}-500"]
                if comp.type in FILLED else [f"text-{c}-600"])
    out += {"lg": ["text-lg"], "sm": ["text-sm"]}.get(s.get("size"), [])
    if s.get("size") == "lg" and comp.type == "button":
        out += ["px-6", "py-3"]
    out += {"bold": ["font-bold"]}.get(s.get("weight"), [])
    out += {"full": ["rounded-full"]}.get(s.get("radius"), [])
    out += {"sticky": ["sticky", "top-0", "z-10", "bg-white"]}.get(s.get("position"), [])
    out += {"center": ["text-center", "self-center"], "right": ["text-right", "self-end"]}.get(s.get("align"), [])
    out += {"dark": ["bg-gray-900", "text-white"]}.get(s.get("theme"), [])
    out += {"md": ["shadow-md"]}.get(s.get("shadow"), [])
    out += {"hidden": ["hidden"]}.get(s.get("display"), [])
    return out


def _cls(comp: Component, extra: str = "") -> str:
    classes = " ".join(filter(None, [BASE.get(comp.type, ""), extra, *style_classes(comp)]))
    return f' class="{classes}"' if classes else ""


def _button_cls(comp: Component, secondary: bool) -> str:
    """Accent fill, unless a colour hint brings its own or it's a Back/Cancel button."""
    if comp.styleHints and comp.styleHints.styles.get("color"):
        return _cls(comp)
    return _cls(comp, SECONDARY if secondary else ACCENT)


def _words(text: str) -> str:
    return " " + re.sub(r"[^a-z0-9]+", " ", text.lower()).strip() + " "


def _has(text: str, words) -> bool:
    return any(f" {w} " in _words(text) for w in words)


def page_name(screen: Screen, index: int) -> str:
    if index == 0:
        return "index.html"
    slug = re.sub(r"[^a-z0-9]+", "-", screen.name.lower()).strip("-") or screen.id
    return f"{slug}.html"


class Nav:
    """Where unlinked buttons on one screen can go: another screen by name, the previous or the next one."""

    def __init__(self, names: dict[str, str] | None = None, prev: str | None = None, next: str | None = None):
        self.names, self.prev, self.next = names or {}, prev, next  # names: screen name -> page file

    def by_name(self, text: str) -> str | None:
        label = _words(text)
        for name, file in sorted(self.names.items(), key=lambda kv: -len(kv[0])):
            if _words(name).strip() and _words(name) in label:
                return file
        return None


def navs(doc: UIDocument) -> dict[str, Nav]:
    """screen id -> Nav; screens keep the order they were drawn in."""
    files = [page_name(s, i) for i, s in enumerate(doc.screens)]
    out = {}
    for i, screen in enumerate(doc.screens):
        names = {s.name: files[j] for j, s in enumerate(doc.screens) if j != i}
        out[screen.id] = Nav(names, files[i - 1] if i else None, files[i + 1] if i + 1 < len(files) else None)
    return out


class _Renderer:
    def __init__(self, link_to: dict[str, str], nav: Nav | None = None):
        self.link_to = link_to  # component id -> page file it opens
        self.nav = nav or Nav()
        self.field_type: dict[str, str] = {}

    def render(self, c: Component, depth: int = 0, parent: Component | None = None) -> str:
        pad = "  " * depth
        p, t = c.props, escape(c.props.text or "")
        if c.type in CONTAINER_TYPES:
            return self._box(c, depth, parent)
        if c.type in app_elements.RENDERERS:
            return app_elements.render(self, c, pad, parent)
        if c.type == "heading":
            level = p.level or 2
            return f'{pad}<h{level}{_cls(c, HEADING_SIZE[level])}>{t}</h{level}>'
        if c.type == "text":
            sized = app_elements.text_size(self, c, parent)  # list-item title/subtitle replaces the body style
            return f'{pad}<p class="{sized}">{t}</p>' if sized else f"{pad}<p{_cls(c)}>{t}</p>"
        if c.type == "button":
            return self._button(c, pad, t)
        label = escape(p.ariaLabel or p.placeholder or p.text or c.type.title())
        if c.type == "input":
            kind = self.field_type.get(c.id, "text")
            ph = f' placeholder="{escape(p.placeholder)}"' if p.placeholder else ""
            return (f'{pad}<label for="{c.id}" class="sr-only">{label}</label>\n'
                    f'{pad}<input id="{c.id}" name="{c.id}" type="{kind}"{ph}{_cls(c)}>')
        if c.type == "textarea":
            ph = f' placeholder="{escape(p.placeholder)}"' if p.placeholder else ""
            return (f'{pad}<label for="{c.id}" class="sr-only">{label}</label>\n'
                    f'{pad}<textarea id="{c.id}" name="{c.id}"{ph}{_cls(c)}></textarea>')
        if c.type == "checkbox":
            checked = " checked" if p.checked else ""
            return (f'{pad}<label class="flex items-center gap-2"><input type="checkbox" name="{c.id}"{checked} '
                    f'class="h-4 w-4 accent-indigo-600"> <span{_cls(c)}>{t}</span></label>')
        if c.type == "dropdown":
            opts = "".join(f"<option>{escape(o)}</option>" for o in (p.options or ["Choose…"]))
            return (f'{pad}<label for="{c.id}" class="sr-only">{label}</label>\n'
                    f'{pad}<select id="{c.id}" name="{c.id}"{_cls(c)}>{opts}</select>')
        if c.type == "image":
            alt = escape(p.alt or "")
            small = app_elements.image_size(parent)  # thumbnails in list items and tiles
            cls = f' class="{small} object-cover ring-1 ring-slate-900/5"' if small else _cls(c, "aspect-[2/1]")
            return f'{pad}<img src="{escape(p.src or IMAGE_PLACEHOLDER)}" alt="{alt}"{cls}>'
        return ""

    def target(self, c: Component, label: str) -> str | None:
        """Where a click goes: drawn arrow > a screen named in the label > Back/Next words."""
        href = self.link_to.get(c.id) or self.nav.by_name(label)
        if not href and _has(label, BACK_WORDS):
            href = self.nav.prev
        if not href and not self.field_type and _has(label, NEXT_WORDS):
            href = self.nav.next
        return href

    def _button(self, c: Component, pad: str, t: str) -> str:
        """Drawn arrow > a screen named in the label > Back/Next words > form submit > a toast."""
        label = c.props.text or ""
        back = _has(label, BACK_WORDS)
        cls = _button_cls(c, secondary=back)
        lead = icons.svg(c.props.icon) if c.props.icon else ""
        t = lead + t
        href = self.target(c, label)
        if href:
            return f'{pad}<a href="{href}"{cls}>{t or "Open"}</a>'
        if self.field_type:  # inside a form: submit it, then go on to the next screen if there is one
            nxt = f' data-next="{self.nav.next}"' if self.nav.next else ""
            return f'{pad}<button type="submit"{nxt}{cls}>{t or "Submit"}</button>'
        msg = next((m for words, m in TOASTS if _has(label, words)), f"{label.strip() or 'Button'} tapped")
        return f'{pad}<button type="button" data-toast="{escape(msg)}"{cls}>{t or "Button"}</button>'

    def _box(self, c: Component, depth: int, parent: Component | None = None) -> str:
        pad = "  " * depth
        tag = {"navbar": "nav", "footer": "footer", "card": "section", "list": "ul", "listitem": "li"}.get(c.type, "div")
        if c.form:
            tag = "form"
            self.field_type = {f.componentId: f.type for f in c.form.fields if f.componentId}
        direction = app_elements.box_layout(c, parent, self)
        inner = "\n".join(self.render(k, depth + 1, c) for k in c.children)
        attrs = _cls(c, direction)
        if tag == "form":
            attrs += f' aria-label="{escape(c.form.name.replace("_", " "))}"'
        out = f"{pad}<{tag}{attrs}>\n{inner}\n{pad}</{tag}>"
        if c.form:
            self.field_type = {}
        return out


def render_screen(screen: Screen, link_to: dict[str, str], nav: Nav | None = None) -> str:
    body = "\n".join(_Renderer(link_to, nav).render(k, 2, screen.root) for k in screen.root.children)
    # leave room for a fixed bottom tab bar
    kinds = {c.type for c in screen.root.walk()}
    main_class = MAIN_CLASS + (" pb-28" if "bottomnav" in kinds else "")
    if kinds & {"chart", "table"}:  # dashboards get the width of a desktop page
        main_class = main_class.replace("max-w-md", "max-w-5xl")
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(screen.name)}</title>
  {TAILWIND}
</head>
<body class="{BODY_CLASS}">
  <main class="{main_class}">
{body}
  </main>
{RUNTIME}
</body>
</html>
"""


def render_site(doc: UIDocument) -> dict[str, str]:
    """{filename: html} for every screen; the first screen is index.html."""
    files = {s.id: page_name(s, i) for i, s in enumerate(doc.screens)}
    nav = navs(doc)
    pages = {}
    for screen in doc.screens:
        link_to = {l.fromComponent: files[l.toScreen] for l in doc.links if l.fromScreen == screen.id}
        pages[files[screen.id]] = render_screen(screen, link_to, nav[screen.id])
    return pages
