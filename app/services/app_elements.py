"""HTML for the app-style elements the vision model reads (icons, tabs, maps, charts, timelines...),
and the context-aware sizing that makes rows, list items and tiles look like the sketch.

Plain markup + Tailwind classes only (no inline style), so react_export can turn it into JSX.
"""
import re
from html import escape

from app.services import icons

# What an icon button does when no arrow was drawn from it
ICON_WORDS = {"back": "back", "close": "close", "arrow": "next"}
ICON_TOAST = {"plus": "Added to cart", "bell": "No new notifications", "search": "Search", "share": "Link copied",
              "phone": "Calling…", "chat": "Opening chat…", "filter": "Filters", "settings": "Settings",
              "menu": "Menu", "cart": "Your cart", "bag": "Your orders", "user": "Your profile",
              "location": "Choose a location", "chevron": "More options", "minus": "Removed one"}
NAV_TITLES = {"home": "Home", "search": "Search", "bag": "Orders", "cart": "Cart", "user": "Profile",
              "heart": "Saved", "bell": "Alerts", "settings": "Settings", "chat": "Chat", "location": "Nearby"}
COLORS = ["#6366f1", "#8b5cf6", "#0ea5e9", "#10b981", "#f59e0b", "#f43f5e"]
SHARES = [34, 24, 18, 14, 10]
ROUND = "grid h-10 w-10 shrink-0 place-items-center rounded-full transition active:scale-95"
WIDE_TYPES = {"chart", "table", "list", "map"}
END_TYPES = {"iconbutton", "icon", "link", "price", "rating", "button", "badge", "toggle"}


def _attrs_compact(r) -> set:
    return r.__dict__.setdefault("compact", set())


def _is_tile(c, parent) -> bool:
    kinds = [k.type for k in c.children]
    return (c.type == "container" and c.layout == "column" and parent is not None and parent.layout == "row"
            and kinds[:1] == ["image"] and len(kinds) <= 2)


def box_layout(c, parent, r=None) -> str:
    """Flex classes for a box, from what it holds and where it sits."""
    kinds = [k.type for k in c.children]
    if c.type == "list":
        return "flex flex-col gap-3"
    if c.type == "listitem":
        return "flex items-center gap-3 rounded-2xl bg-white p-3 shadow-sm ring-1 ring-slate-900/5"
    if c.layout == "row":
        if set(kinds) & WIDE_TYPES or (len(kinds) > 1 and set(kinds) <= {"card", "image"}):
            return f"grid items-start gap-4 sm:grid-cols-{min(len(kinds), 4)}"  # dashboard panels side by side
        if any(_is_tile(k, c) for k in c.children):
            return "flex justify-between gap-3 overflow-x-auto pb-1"
        if kinds and set(kinds) == {"button"} and len(kinds) > 1:
            return f"grid grid-cols-{min(len(kinds), 4)} gap-3"
        spread = len(kinds) > 1 and kinds[-1] in END_TYPES
        return "flex items-center gap-3" + (" justify-between" if spread else " flex-wrap")
    if c.type == "container" and parent is not None and parent.layout == "row":
        if _is_tile(c, parent):
            if r is not None:
                _attrs_compact(r).add(("tile", c.id))
            return "flex w-16 shrink-0 flex-col items-center gap-1.5 text-center"
        if r is not None:
            _attrs_compact(r).add(("stack", c.id))
        return "flex min-w-0 flex-1 flex-col gap-0.5"
    return "flex flex-col gap-4" if c.type == "container" else "flex flex-col gap-3"


def text_size(r, c, parent) -> str:
    """Titles and subtitles inside list items and tiles."""
    marks = _attrs_compact(r)
    if parent is None:
        return ""
    if parent.type == "card" and re.fullmatch(r"[₹$€£]?\s?[\d.,]+[%kKmM+]?", (c.props.text or "").strip()):
        return "text-3xl font-bold tracking-tight text-slate-900"  # a stat tile's number
    if ("tile", parent.id) in marks:
        return "text-xs font-medium text-slate-700"
    if ("stack", parent.id) in marks:
        texts = [k.id for k in parent.children if k.type == "text"]
        return "font-semibold text-slate-900 truncate" if texts and texts[0] == c.id else "text-sm text-slate-500 truncate"
    return ""


def image_size(parent) -> str:
    if parent is not None and parent.type == "listitem":
        return "h-16 w-16 shrink-0 rounded-xl"
    if parent is not None and parent.layout == "column" and [k.type for k in parent.children][:1] == ["image"] \
            and len(parent.children) <= 2 and parent.type == "container":
        return "h-14 w-14 rounded-2xl"
    return ""


def _icon(r, c, pad, parent):
    tone = "text-indigo-600" if c.props.icon == "location" else "text-slate-700"
    return f'{pad}<span class="inline-grid h-8 w-8 shrink-0 place-items-center {tone}">{icons.svg(c.props.icon)}</span>'


def _iconbutton(r, c, pad, parent):
    name = icons.name_of(c.props.icon)
    label = escape(c.props.ariaLabel or name.title())
    if name == "heart":
        return (f'{pad}<button type="button" data-fav aria-pressed="false" aria-label="Save"'
                f' class="{ROUND} text-slate-400 hover:text-rose-500">{icons.svg(name)}</button>')
    style = ("rounded-xl bg-indigo-600 text-white shadow-sm shadow-indigo-600/30 hover:bg-indigo-500" if name == "plus"
             else "bg-white text-slate-700 shadow-sm ring-1 ring-slate-900/5 hover:bg-slate-50")
    href = r.target(c, ICON_WORDS.get(name, name))
    if href:
        return f'{pad}<a href="{href}" aria-label="{label}" class="{ROUND} {style}">{icons.svg(name)}</a>'
    msg = escape(ICON_TOAST.get(name, label))
    return f'{pad}<button type="button" data-toast="{msg}" aria-label="{label}" class="{ROUND} {style}">{icons.svg(name)}</button>'


def _search(r, c, pad, parent):
    ph = escape(c.props.placeholder or "Search")
    return (f'{pad}<div class="relative">\n'
            f'{pad}  <span class="pointer-events-none absolute inset-y-0 left-4 grid place-items-center text-slate-400">{icons.svg("search", "h-4 w-4")}</span>\n'
            f'{pad}  <label for="{c.id}" class="sr-only">{ph}</label>\n'
            f'{pad}  <input id="{c.id}" name="{c.id}" type="search" placeholder="{ph}" class="w-full rounded-2xl border-0 bg-white py-3 pl-11 pr-4 text-sm shadow-sm ring-1 ring-inset ring-slate-200 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500">\n'
            f'{pad}</div>')


def _link(r, c, pad, parent):
    text = escape(c.props.text or "See all")
    cls = "shrink-0 text-sm font-semibold text-indigo-600 hover:text-indigo-500"
    href = r.target(c, c.props.text or "")
    if href:
        return f'{pad}<a href="{href}" class="{cls}">{text}</a>'
    return f'{pad}<button type="button" data-toast="Showing everything" class="{cls}">{text}</button>'


def _carousel(r, c, pad, parent):
    from app.services.codegen_service import IMAGE_PLACEHOLDER
    alt = escape(c.props.alt or "")
    caption = (f'\n{pad}    <div class="absolute inset-x-0 bottom-0 bg-gradient-to-t from-slate-900/60 to-transparent p-4">'
               f'<p class="font-semibold text-white">{alt}</p></div>') if alt else ""
    return (f'{pad}<div class="space-y-3">\n'
            f'{pad}  <div class="relative overflow-hidden rounded-3xl shadow-sm ring-1 ring-slate-900/5">\n'
            f'{pad}    <img src="{IMAGE_PLACEHOLDER}" alt="{alt}" class="aspect-[2/1] w-full object-cover">{caption}\n'
            f'{pad}  </div>\n'
            f'{pad}  <div class="flex justify-center gap-1.5" aria-hidden="true"><span class="h-1.5 w-5 rounded-full bg-indigo-600"></span>'
            f'<span class="h-1.5 w-1.5 rounded-full bg-slate-300"></span><span class="h-1.5 w-1.5 rounded-full bg-slate-300"></span></div>\n'
            f'{pad}</div>')


def _tabs(r, c, pad, parent):
    labels = c.props.options or ["Overview", "Menu", "Reviews"]
    tabs = "".join(
        f'<button type="button" role="tab" aria-selected="{"true" if i == 0 else "false"}" class="-mb-px border-b-2 pb-2.5 text-sm font-semibold transition '
        f'{"border-indigo-600 text-indigo-600" if i == 0 else "border-transparent text-slate-500"}">{escape(t)}</button>'
        for i, t in enumerate(labels))
    return f'{pad}<div role="tablist" class="flex gap-6 border-b border-slate-200">{tabs}</div>'


def _bottomnav(r, c, pad, parent):
    items = []
    for i, raw in enumerate(c.props.options or ["home", "search", "bag", "user"]):
        name = icons.name_of(raw)
        title = escape(NAV_TITLES.get(name, raw.strip().title()))
        tone = "text-indigo-600" if i == 0 else "text-slate-400 hover:text-slate-700"
        body = f'{icons.svg(name, "h-6 w-6")}<span class="text-[11px] font-medium">{title}</span>'
        cls = f"flex flex-col items-center gap-1 {tone}"
        href = r.nav.by_name(NAV_TITLES.get(name, raw))
        if href:
            items.append(f'<a href="{href}" class="{cls}">{body}</a>')
        elif i == 0:
            items.append(f'<a href="#" aria-current="page" class="{cls}">{body}</a>')
        else:
            items.append(f'<button type="button" data-toast="{title}" class="{cls}">{body}</button>')
    return (f'{pad}<nav aria-label="Main" class="fixed inset-x-0 bottom-0 z-20 mx-auto max-w-md border-t border-slate-200 '
            f'bg-white/90 px-8 pb-5 pt-3 backdrop-blur">\n{pad}  <div class="flex justify-between">{"".join(items)}</div>\n{pad}</nav>')


def _map(r, c, pad, parent):
    roads = "".join(f'<path d="{d}" stroke="#ffffff" stroke-width="10" fill="none"/>' for d in
                    ("M-10 60 L410 20", "M-10 150 L410 110", "M80 -10 L130 210", "M250 -10 L300 210", "M360 -10 L330 210"))
    return (f'{pad}<div role="img" aria-label="{escape(c.props.text or "Map with the delivery route")}" class="relative h-52 overflow-hidden rounded-3xl bg-slate-100 shadow-sm ring-1 ring-slate-900/5">\n'
            f'{pad}  <svg viewBox="0 0 400 200" preserveAspectRatio="xMidYMid slice" class="h-full w-full" aria-hidden="true">'
            f'<rect width="400" height="200" fill="#e8edf5"/><rect x="150" y="70" width="80" height="45" rx="6" fill="#d9f2e3"/>{roads}'
            f'<path d="M70 150 L140 128 L190 140 L230 100 L330 70" stroke="#6366f1" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" fill="none"/>'
            f'<circle cx="70" cy="150" r="9" fill="#ffffff" stroke="#6366f1" stroke-width="4"/>'
            f'<circle cx="330" cy="70" r="11" fill="#6366f1"/><circle cx="330" cy="70" r="4" fill="#ffffff"/></svg>\n'
            f'{pad}</div>')


def _progress(r, c, pad, parent):
    v = max(0, min(100, round(c.props.value or 60)))
    return (f'{pad}<div class="space-y-1.5">\n'
            f'{pad}  <div class="flex justify-between text-xs font-medium text-slate-500"><span>{escape(c.props.text or "Progress")}</span><span>{v}%</span></div>\n'
            f'{pad}  <div role="progressbar" aria-valuenow="{v}" aria-valuemin="0" aria-valuemax="100" aria-label="{escape(c.props.text or "Progress")}" class="h-2.5 overflow-hidden rounded-full bg-slate-200">'
            f'<div class="h-full w-[{v}%] rounded-full bg-gradient-to-r from-indigo-500 to-violet-500"></div></div>\n'
            f'{pad}</div>')


def _timeline(r, c, pad, parent):
    steps = c.props.options or ["Ordered", "Packed", "On the way", "Delivered"]
    cur = int(c.props.value) if c.props.value is not None else 1
    out = []
    for i, label in enumerate(steps):
        if i < cur:
            mark, sub = f'<span class="grid h-7 w-7 place-items-center rounded-full bg-indigo-600 text-white">{icons.svg("check", "h-4 w-4")}</span>', "Done"
        elif i == cur:
            mark, sub = '<span class="grid h-7 w-7 place-items-center rounded-full border-2 border-indigo-600 bg-white ring-4 ring-indigo-100"><span class="h-2.5 w-2.5 rounded-full bg-indigo-600"></span></span>', "In progress"
        else:
            mark, sub = '<span class="h-7 w-7 rounded-full border-2 border-slate-300 bg-white"></span>', "Pending"
        line = '<span class="absolute left-[13px] top-8 h-[calc(100%-4px)] w-0.5 bg-slate-200" aria-hidden="true"></span>' if i < len(steps) - 1 else ""
        tone = "text-slate-900" if i <= cur else "text-slate-400"
        out.append(f'{pad}  <li class="relative flex gap-3 pb-5">{line}{mark}<div><p class="text-sm font-semibold {tone}">{escape(label)}</p>'
                   f'<p class="text-xs text-slate-500">{sub}</p></div></li>')
    return f'{pad}<ol class="pl-1">\n' + "\n".join(out) + f'\n{pad}</ol>'


def _chart(r, c, pad, parent):
    kind = c.props.variant or "bar"
    labels = c.props.options or ["Mon", "Tue", "Wed", "Thu", "Fri"]
    vals = [SHARES[i % len(SHARES)] for i in range(len(labels))]
    legend = "".join(f'<li class="flex items-center gap-2 text-sm text-slate-600"><span class="h-2.5 w-2.5 rounded-full bg-[{COLORS[i % len(COLORS)]}]"></span>'
                     f'{escape(l)}<span class="ml-auto font-medium text-slate-900">{v}%</span></li>' for i, (l, v) in enumerate(zip(labels, vals)))
    title = escape(c.props.text or "")
    if kind in ("pie", "donut"):
        # each slice is a dashed circle stroke; r=15.915 makes the circumference 100, so dashes are percents
        width, size = (6, 42) if kind == "donut" else (31.83, 64)
        total, offset, segs = sum(vals), 25.0, []
        for i, v in enumerate(vals):
            share = 100 * v / total
            segs.append(f'<circle cx="{size / 2:g}" cy="{size / 2:g}" r="15.915" fill="none" stroke="{COLORS[i % len(COLORS)]}" '
                        f'stroke-width="{width}" stroke-dasharray="{share:.2f} {100 - share:.2f}" stroke-dashoffset="{offset:.2f}"/>')
            offset -= share
        graphic = f'<svg viewBox="0 0 {size} {size}" class="h-36 w-36 shrink-0" aria-hidden="true">{"".join(segs)}</svg>'
        body = f'<div class="flex flex-wrap items-center justify-center gap-6">{graphic}<ul class="min-w-[8rem] flex-1 space-y-2">{legend}</ul></div>'
    elif kind == "line":
        wave = [52, 64, 58, 40, 46, 78, 96][: max(len(labels), 2)]
        xy = [(i * 300 / (len(wave) - 1), 120 - v) for i, v in enumerate(wave)]
        line = " ".join(f"{x:.0f},{y:.0f}" for x, y in xy)
        body = (f'<svg viewBox="0 0 300 120" preserveAspectRatio="none" class="h-44 w-full" aria-hidden="true">'
                f'<polygon points="0,120 {line} 300,120" fill="#6366f1" fill-opacity="0.1"/>'
                f'<polyline points="{line}" fill="none" stroke="#6366f1" stroke-width="3" stroke-linecap="round" '
                f'stroke-linejoin="round" vector-effect="non-scaling-stroke"/></svg>'
                f'<div class="mt-2 flex justify-between text-xs text-slate-500">{"".join(f"<span>{escape(l)}</span>" for l in labels)}</div>')
    else:
        bars = "".join(f'<div class="flex flex-1 flex-col items-center gap-2"><div class="flex h-36 w-full items-end"><div class="h-[{v * 2.5:.0f}%] w-full rounded-t-lg bg-gradient-to-t from-indigo-500 to-violet-400"></div></div>'
                       f'<span class="text-xs text-slate-500">{escape(l)}</span></div>' for l, v in zip(labels, vals))
        body = f'<div class="flex items-end gap-3">{bars}</div>'
    head = f'<p class="mb-4 font-semibold text-slate-900">{title}</p>' if title and title.lower() not in ("pie", "bar", "line", "donut") else ""
    summary = escape(", ".join(f"{l} {v}%" for l, v in zip(labels, vals)))
    return f'{pad}<figure role="img" aria-label="{kind} chart: {summary}" class="rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-900/5">{head}{body}</figure>'


def _table(r, c, pad, parent):
    cols = c.props.options or ["Name", "Status", "Amount"]
    head = "".join(f'<th scope="col" class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">{escape(h)}</th>' for h in cols)
    rows = "".join("<tr class=\"border-t border-slate-100\">" + "".join(
        f'<td class="px-4 py-3 text-slate-700">{escape(h)} {n}</td>' for h in cols) + "</tr>" for n in range(1, 4))
    return (f'{pad}<div class="overflow-x-auto rounded-2xl bg-white shadow-sm ring-1 ring-slate-900/5">'
            f'<table class="w-full text-sm"><thead class="bg-slate-50"><tr>{head}</tr></thead><tbody>{rows}</tbody></table></div>')


def _rating(r, c, pad, parent):
    v = c.props.value or 4.5
    return (f'{pad}<span class="inline-flex w-fit items-center gap-1 text-sm font-semibold text-slate-700" aria-label="Rated {v:.1f} out of 5">'
            f'<svg viewBox="0 0 24 24" class="h-4 w-4 text-amber-400" fill="currentColor" aria-hidden="true"><path d="{icons.PATHS["star"]}"/></svg>{v:.1f}</span>')


def _price(r, c, pad, parent):
    return f'{pad}<span class="text-sm font-bold text-slate-900">{escape(c.props.text or "")}</span>'


def _badge(r, c, pad, parent):
    return f'{pad}<span class="inline-flex w-fit rounded-full bg-indigo-50 px-2.5 py-0.5 text-xs font-semibold text-indigo-700">{escape(c.props.text or "")}</span>'


def _toggle(r, c, pad, parent):
    label = escape(c.props.text or "Enabled")
    return (f'{pad}<label class="flex cursor-pointer items-center justify-between gap-3"><span class="text-sm font-medium text-slate-700">{label}</span>'
            f'<input type="checkbox" role="switch" name="{c.id}" class="peer sr-only">'
            f'<span class="relative h-6 w-11 shrink-0 rounded-full bg-slate-300 transition peer-checked:bg-indigo-600 peer-focus-visible:ring-2 peer-focus-visible:ring-indigo-500 '
            f'after:absolute after:left-0.5 after:top-0.5 after:h-5 after:w-5 after:rounded-full after:bg-white after:shadow after:transition peer-checked:after:translate-x-5"></span></label>')


def _slider(r, c, pad, parent):
    label = escape(c.props.ariaLabel or c.props.text or "Value")
    return (f'{pad}<label for="{c.id}" class="sr-only">{label}</label>\n'
            f'{pad}<input id="{c.id}" name="{c.id}" type="range" min="0" max="100" value="{round(c.props.value or 50)}" class="w-full accent-indigo-600">')


RENDERERS = {
    "icon": _icon, "iconbutton": _iconbutton, "search": _search, "link": _link, "carousel": _carousel,
    "tabs": _tabs, "bottomnav": _bottomnav, "map": _map, "progress": _progress, "timeline": _timeline,
    "chart": _chart, "table": _table, "rating": _rating, "price": _price, "badge": _badge,
    "toggle": _toggle, "slider": _slider,
}


def render(r, c, pad, parent) -> str:
    return RENDERERS[c.type](r, c, pad, parent)
