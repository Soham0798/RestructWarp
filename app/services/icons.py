"""Stroke icons (Lucide-style paths) drawn inline in generated pages, so they need no icon font."""
PATHS = {
    "back": "M15 18l-6-6 6-6",
    "chevron": "M6 9l6 6 6-6",
    "arrow": "M5 12h14 M13 6l6 6-6 6",
    "menu": "M4 6h16 M4 12h16 M4 18h16",
    "search": "M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14z M21 21l-4.3-4.3",
    "bell": "M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9 M10.3 21a1.9 1.9 0 0 0 3.4 0",
    "heart": "M19 14c1.5-1.5 3-3.2 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.8 0-3 .5-4.5 2-1.5-1.5-2.7-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4 3 5.5l7 7z",
    "location": "M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0z M12 7a3 3 0 1 0 0 6 3 3 0 0 0 0-6z",
    "home": "M3 10l9-7 9 7v10a2 2 0 0 1-2 2h-4v-7H9v7H5a2 2 0 0 1-2-2z",
    "cart": "M3 3h2l2.4 12.2a2 2 0 0 0 2 1.6h8.8a2 2 0 0 0 2-1.6L22 7H6 M9 21a1 1 0 1 0 0 .01 M18 21a1 1 0 1 0 0 .01",
    "bag": "M6 7h12l1 14H5z M9 7a3 3 0 0 1 6 0",
    "user": "M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8z M4 21a8 8 0 0 1 16 0",
    "star": "M12 2l3.1 6.3 6.9 1-5 4.9 1.2 6.8L12 17.8 5.8 21l1.2-6.8-5-4.9 6.9-1z",
    "plus": "M12 5v14 M5 12h14",
    "minus": "M5 12h14",
    "phone": "M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1 1 .4 1.9.7 2.8a2 2 0 0 1-.5 2.1L8 9.9a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.4c.9.3 1.8.6 2.8.7a2 2 0 0 1 1.7 2z",
    "chat": "M21 12a8 8 0 0 1-11.6 7.1L3 21l1.9-6.4A8 8 0 1 1 21 12z",
    "truck": "M1 4h14v12H1z M15 9h4l3 3v4h-7 M5.5 19a1.5 1.5 0 1 0 0 .01 M18.5 19a1.5 1.5 0 1 0 0 .01",
    "filter": "M3 5h18l-7 8v6l-4 2v-8z",
    "settings": "M12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6z M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z",
    "share": "M18 8a3 3 0 1 0 0-6 3 3 0 0 0 0 6z M6 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z M18 22a3 3 0 1 0 0-6 3 3 0 0 0 0 6z M8.6 13.5l6.8 4 M15.4 6.5l-6.8 4",
    "close": "M18 6L6 18 M6 6l12 12",
    "check": "M5 12l5 5L20 7",
    "image": "M4 4h16v16H4z M4 16l5-5 4 4 3-3 4 4",
}
# Words people (or the model) use for the same icon
ALIASES = {"location-pin": "location", "pin": "location", "map-pin": "location", "notification": "bell",
           "notifications": "bell", "like": "heart", "favorite": "heart", "favourite": "heart", "profile": "user",
           "account": "user", "person": "user", "basket": "cart", "shopping": "bag", "add": "plus",
           "next": "arrow", "forward": "arrow", "left": "back", "call": "phone", "message": "chat",
           "delivery": "truck", "x": "close", "hamburger": "menu", "down": "chevron", "dropdown": "chevron"}


def name_of(raw: str | None) -> str:
    key = (raw or "").strip().lower()
    key = ALIASES.get(key, key)
    return key if key in PATHS else "image"


def svg(name: str, cls: str = "h-5 w-5") -> str:
    return (f'<svg viewBox="0 0 24 24" class="{cls}" fill="none" stroke="currentColor" stroke-width="2" '
            f'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="{PATHS[name_of(name)]}"/></svg>')
