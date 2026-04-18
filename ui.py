from __future__ import annotations

import threading

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import GLib, Gtk

from gtk_style import THEMES, install_css
from network_forensics import collect_connections, reverse_dns
from settings import load_settings, save_settings
from updater import can_launch_updates_from_app, check_all_updates, detect_managers, run_update_in_terminal


class OpsConsoleApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="org.evans.OpsConsole")
        self.window: Gtk.ApplicationWindow | None = None
        self.css_provider: Gtk.CssProvider | None = None

        self.settings = load_settings()
        self.theme_name = self.settings.get("theme", "dark")
        if self.theme_name not in THEMES:
            self.theme_name = "dark"
        self.system_manager = "none"
        self.conn_rows = []

        self.refresh_spin: Gtk.SpinButton | None = None
        self.status_label: Gtk.Label | None = None
        self.detected_label: Gtk.Label | None = None
        self.theme_dropdown: Gtk.DropDown | None = None
        self.conn_list: Gtk.ListBox | None = None
        self.update_buffer: Gtk.TextBuffer | None = None

    def do_activate(self):
        if self.window is None:
            self._build_ui()
            self._refresh_connections_once()
            self.refresh_updates()
            GLib.timeout_add(int(self.settings.get("refresh_interval_ms", 1200)), self._scheduled_refresh)
        self.window.present()

    def _build_ui(self):
        self.window = Gtk.ApplicationWindow(application=self)
        self.window.set_title("Ops Console")
        self.window.set_default_size(1180, 760)
        self.window.set_size_request(980, 640)
        self.css_provider = install_css(self.window, self.theme_name)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        root.set_margin_top(12)
        root.set_margin_bottom(12)
        root.set_margin_start(12)
        root.set_margin_end(12)
        self.window.set_child(root)

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        header.add_css_class("toolbar")
        header.add_css_class("section")
        root.append(header)

        titles = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        titles.set_hexpand(True)
        header.append(titles)

        title = Gtk.Label(label="Ops Console")
        title.set_xalign(0.0)
        title.add_css_class("title-1")
        titles.append(title)

        subtitle = Gtk.Label(label="Network Forensics + Update Orchestrator")
        subtitle.set_xalign(0.0)
        subtitle.add_css_class("dim-label")
        titles.append(subtitle)

        self.theme_dropdown = Gtk.DropDown.new_from_strings(["dark", "light"])
        self.theme_dropdown.set_selected(0 if self.theme_name == "dark" else 1)
        self.theme_dropdown.connect("notify::selected", self._on_theme_changed)
        header.append(self.theme_dropdown)

        notebook = Gtk.Notebook()
        notebook.set_hexpand(True)
        notebook.set_vexpand(True)
        root.append(notebook)

        notebook.append_page(self._build_network_tab(), Gtk.Label(label="Network"))
        notebook.append_page(self._build_updates_tab(), Gtk.Label(label="Updates"))

        self.status_label = Gtk.Label(label="Ready")
        self.status_label.set_xalign(0.0)
        self.status_label.add_css_class("dim-label")
        root.append(self.status_label)

    def _build_network_tab(self) -> Gtk.Widget:
        tab = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)

        controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        controls.add_css_class("section")
        tab.append(controls)

        refresh_btn = Gtk.Button(label="Refresh")
        refresh_btn.add_css_class("pill")
        refresh_btn.connect("clicked", lambda _b: self._refresh_connections_once())
        controls.append(refresh_btn)

        label = Gtk.Label(label="Interval (ms)")
        label.add_css_class("dim-label")
        controls.append(label)

        adjustment = Gtk.Adjustment(
            value=float(self.settings.get("refresh_interval_ms", 1200)),
            lower=300,
            upper=5000,
            step_increment=100,
            page_increment=100,
            page_size=0,
        )
        self.refresh_spin = Gtk.SpinButton(adjustment=adjustment, climb_rate=0, digits=0)
        self.refresh_spin.connect("value-changed", self._on_refresh_interval)
        controls.append(self.refresh_spin)

        scroller = Gtk.ScrolledWindow()
        scroller.set_hexpand(True)
        scroller.set_vexpand(True)
        scroller.add_css_class("card")
        tab.append(scroller)

        self.conn_list = Gtk.ListBox()
        self.conn_list.add_css_class("boxed-list")
        self.conn_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.conn_list.connect("row-activated", self._on_connection_activated)
        scroller.set_child(self.conn_list)
        return tab

    def _build_updates_tab(self) -> Gtk.Widget:
        tab = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)

        controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        controls.add_css_class("section")
        tab.append(controls)

        refresh_btn = Gtk.Button(label="Check Updates")
        refresh_btn.add_css_class("pill")
        refresh_btn.connect("clicked", lambda _b: self.refresh_updates())
        controls.append(refresh_btn)

        self.system_update_btn = Gtk.Button(label="Run System Update")
        self.system_update_btn.add_css_class("flat-pill")
        self.system_update_btn.connect("clicked", lambda _b: self._run_system_update())
        controls.append(self.system_update_btn)

        self.flatpak_update_btn = Gtk.Button(label="Run Flatpak Update")
        self.flatpak_update_btn.add_css_class("flat-pill")
        self.flatpak_update_btn.connect("clicked", lambda _b: self._run_flatpak_update())
        controls.append(self.flatpak_update_btn)

        self.detected_label = Gtk.Label(label="Managers: -")
        self.detected_label.add_css_class("dim-label")
        controls.append(self.detected_label)

        scroller = Gtk.ScrolledWindow()
        scroller.set_hexpand(True)
        scroller.set_vexpand(True)
        scroller.add_css_class("card")
        tab.append(scroller)

        text = Gtk.TextView()
        text.set_editable(False)
        text.set_monospace(True)
        text.set_wrap_mode(Gtk.WrapMode.WORD)
        self.update_buffer = text.get_buffer()
        scroller.set_child(text)
        return tab

    def _on_theme_changed(self, dropdown: Gtk.DropDown, _param: object):
        item = dropdown.get_selected_item()
        if item is None:
            return
        theme_name = item.get_string()
        self.apply_theme(theme_name)

    def apply_theme(self, theme_name: str):
        if theme_name not in THEMES:
            theme_name = "dark"
        self.theme_name = theme_name
        self.settings["theme"] = theme_name
        save_settings(self.settings)
        if self.window is not None:
            self.css_provider = install_css(self.window, theme_name)

    def _on_refresh_interval(self, _spin: Gtk.SpinButton):
        if self.refresh_spin is None:
            return
        value = int(self.refresh_spin.get_value())
        value = max(300, min(5000, value))
        self.refresh_spin.set_value(value)
        self.settings["refresh_interval_ms"] = value
        save_settings(self.settings)
        self._set_status(f"Refresh interval set to {value} ms")

    def _scheduled_refresh(self) -> bool:
        self._refresh_connections_once(set_status=False)
        GLib.timeout_add(int(self.settings.get("refresh_interval_ms", 1200)), self._scheduled_refresh)
        return False

    def _refresh_connections_once(self, set_status: bool = True):
        known = self.settings.get("known_processes", [])
        rows = collect_connections(known)
        self.conn_rows = rows

        if self.conn_list is not None:
            while True:
                row = self.conn_list.get_row_at_index(0)
                if row is None:
                    break
                self.conn_list.remove(row)

            for idx, row_data in enumerate(rows):
                row = self._make_connection_row(idx, row_data)
                self.conn_list.append(row)

        if set_status:
            alerts = sum(1 for r in rows if r.suspicious)
            self._set_status(f"Connections: {len(rows)} | Alerts: {alerts}")

    def _make_connection_row(self, index: int, row_data) -> Gtk.ListBoxRow:
        row = Gtk.ListBoxRow()
        row.set_name(str(index))

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        outer.set_margin_top(6)
        outer.set_margin_bottom(6)
        outer.set_margin_start(8)
        outer.set_margin_end(8)
        row.set_child(outer)

        title = Gtk.Label(label=f"{'! ' if row_data.suspicious else ''}{row_data.process} (PID {row_data.pid})")
        title.set_xalign(0.0)
        outer.append(title)

        meta = Gtk.Label(label=f"Local: {row_data.laddr}   Remote: {row_data.raddr}")
        meta.set_xalign(0.0)
        meta.set_wrap(True)
        meta.add_css_class("dim-label")
        outer.append(meta)

        state = Gtk.Label(label=f"State: {row_data.status}")
        state.set_xalign(0.0)
        outer.append(state)
        return row

    def _on_connection_activated(self, _listbox: Gtk.ListBox, row: Gtk.ListBoxRow):
        try:
            row_data = self.conn_rows[int(row.get_name())]
        except Exception:
            return
        remote = row_data.raddr
        if remote == "-":
            self._show_message("Connection", "No remote address for this socket.")
            return
        host = remote.split(":", 1)[0]
        dns = reverse_dns(host)
        self._show_message("Reverse DNS", f"IP: {host}\nHost: {dns}")

    def refresh_updates(self):
        managers = detect_managers()
        if self.detected_label is not None:
            self.detected_label.set_text(f"Managers: {', '.join(managers) if managers else 'none'}")
        self.system_manager = "pacman" if "pacman" in managers else ("apt" if "apt" in managers else "none")
        can_launch, reason = can_launch_updates_from_app()
        self.system_update_btn.set_sensitive(can_launch and self.system_manager != "none")
        self.flatpak_update_btn.set_sensitive(can_launch and ("flatpak" in managers))
        if not can_launch and reason:
            self._set_status(reason)

        def task():
            results = check_all_updates()
            GLib.idle_add(self._render_updates, results)

        threading.Thread(target=task, daemon=True).start()

    def _run_system_update(self):
        if self.system_manager == "none":
            self._show_message("System Update", "No supported system package manager detected (pacman/apt).")
            return
        ok, info = run_update_in_terminal(self.system_manager)
        if ok:
            self._set_status(info)
            return
        self._set_status("Failed to launch system update")
        self._show_message("System Update", info)

    def _run_flatpak_update(self):
        managers = detect_managers()
        if "flatpak" not in managers:
            self._show_message("Flatpak Update", "Flatpak is not available on this system.")
            return
        ok, info = run_update_in_terminal("flatpak")
        if ok:
            self._set_status(info)
            return
        self._set_status("Failed to launch Flatpak update")
        self._show_message("Flatpak Update", info)

    def _render_updates(self, results):
        lines = []
        for result in results:
            lines.append(f"[{result.manager}] {result.summary}")
            lines.append(f"Command: {result.command}")
            if result.details:
                lines.append(result.details)
            lines.append("-" * 50)
        text = "\n".join(lines) if lines else "No supported managers detected."
        if self.update_buffer is not None:
            self.update_buffer.set_text(text)
        self._set_status("Update check finished")
        return False

    def _show_message(self, title: str, body: str):
        if self.window is None:
            return
        dialog = Gtk.MessageDialog(
            transient_for=self.window,
            modal=True,
            buttons=Gtk.ButtonsType.OK,
            text=title,
            secondary_text=body,
        )
        dialog.connect("response", lambda d, _r: d.close())
        dialog.present()

    def _set_status(self, text: str):
        if self.status_label is not None:
            self.status_label.set_text(text)
