from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

THEMES: dict[str, dict[str, str]] = {
    "dark": {
        "window_bg": "#0f172a",
        "panel_bg": "#111827",
        "card_bg": "#0b1220",
        "border": "#1f2937",
        "text": "#e2e8f0",
        "muted": "#94a3b8",
        "entry_bg": "#020617",
        "entry_fg": "#dbeafe",
        "accent": "#2563eb",
        "accent_hover": "#3b82f6",
        "accent_active": "#1d4ed8",
        "accent_fg": "#eff6ff",
        "row_hover": "rgba(59, 130, 246, 0.18)",
        "row_selected": "rgba(37, 99, 235, 0.30)",
    },
    "light": {
        "window_bg": "#eff4fb",
        "panel_bg": "#ffffff",
        "card_bg": "#f8fbff",
        "border": "#d7e1ee",
        "text": "#0f172a",
        "muted": "#475569",
        "entry_bg": "#ffffff",
        "entry_fg": "#0f172a",
        "accent": "#2563eb",
        "accent_hover": "#3b82f6",
        "accent_active": "#1d4ed8",
        "accent_fg": "#eff6ff",
        "row_hover": "rgba(59, 130, 246, 0.08)",
        "row_selected": "rgba(37, 99, 235, 0.16)",
    },
}


def _css(theme: str) -> bytes:
    palette = THEMES.get(theme, THEMES["dark"])
    return f"""
window,
.background {{
  background: {palette['window_bg']};
  color: {palette['text']};
}}

headerbar,
.toolbar,
.section,
.card,
list.boxed-list,
entry,
dropdown,
spinbutton,
notebook > stack,
scrolledwindow,
textview,
frame > border {{
  background: {palette['panel_bg']};
  color: {palette['text']};
}}

.section,
.card,
entry,
dropdown,
spinbutton,
scrolledwindow,
textview,
list.boxed-list,
frame > border,
notebook > stack {{
  border-radius: 18px;
  border: 1px solid {palette['border']};
}}

entry,
spinbutton,
textview text {{
  background: {palette['entry_bg']};
  color: {palette['entry_fg']};
}}

label,
entry,
button,
textview {{
  color: {palette['text']};
}}

.title-1 {{
  color: {palette['text']};
  font-weight: 800;
  letter-spacing: 0.02em;
}}

.dim-label {{
  color: {palette['muted']};
}}

button {{
  border-radius: 999px;
  min-height: 38px;
  padding: 8px 16px;
}}

button.pill {{
  background: {palette['accent']};
  color: {palette['accent_fg']};
  border: 1px solid {palette['accent']};
}}

button.pill:hover {{
  background: {palette['accent_hover']};
}}

button.pill:active {{
  background: {palette['accent_active']};
}}

button.flat-pill {{
  background: transparent;
  border: 1px solid {palette['border']};
}}

list.boxed-list row {{
  margin: 4px 6px;
  border-radius: 14px;
  padding: 8px;
  background: {palette['card_bg']};
}}

list.boxed-list row:hover {{
  background: {palette['row_hover']};
}}

list.boxed-list row:selected {{
  background: {palette['row_selected']};
}}

notebook > header > tabs > tab {{
  border-radius: 999px;
  padding: 8px 14px;
}}
""".encode("utf-8")


def install_css(window: Gtk.Window, theme: str) -> Gtk.CssProvider:
    provider = Gtk.CssProvider()
    provider.load_from_data(_css(theme))
    display = window.get_display()
    Gtk.StyleContext.add_provider_for_display(
        display,
        provider,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
    )
    return provider
