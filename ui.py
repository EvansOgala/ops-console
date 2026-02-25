import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from network_forensics import collect_connections, reverse_dns
from settings import load_settings, save_settings
from updater import can_launch_updates_from_app, check_all_updates, detect_managers, run_update_in_terminal

THEMES = {
    "dark": {
        "root": "#0f172a",
        "panel": "#111827",
        "card": "#0b1220",
        "line": "#1f2937",
        "text": "#e2e8f0",
        "muted": "#94a3b8",
        "entry": "#020617",
        "entry_fg": "#dbeafe",
        "accent": "#2563eb",
        "accent_hover": "#3b82f6",
        "accent_press": "#1d4ed8",
        "accent_text": "#eff6ff",
        "select": "#2563eb",
        "warn": "#f87171",
    },
    "light": {
        "root": "#f1f5f9",
        "panel": "#ffffff",
        "card": "#f8fafc",
        "line": "#dbe3ee",
        "text": "#0f172a",
        "muted": "#475569",
        "entry": "#ffffff",
        "entry_fg": "#0f172a",
        "accent": "#2563eb",
        "accent_hover": "#3b82f6",
        "accent_press": "#1d4ed8",
        "accent_text": "#eff6ff",
        "select": "#93c5fd",
        "warn": "#dc2626",
    },
}


class RoundedButton(tk.Canvas):
    def __init__(self, parent, text, command, width=118, height=34, radius=14):
        super().__init__(parent, width=width, height=height, bd=0, highlightthickness=0, relief="flat", cursor="hand2")
        self.command = command
        self.text = text
        self.width = width
        self.height = height
        self.radius = radius
        self.pressed = False
        self.enabled = True
        self.colors = {
            "bg": "#2563eb",
            "hover": "#3b82f6",
            "press": "#1d4ed8",
            "fg": "#eff6ff",
            "container": "#0f172a",
            "disabled": "#475569",
        }
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
        self._draw()

    def configure_theme(self, palette, container_bg):
        self.colors.update(
            {
                "bg": palette["accent"],
                "hover": palette["accent_hover"],
                "press": palette["accent_press"],
                "fg": palette["accent_text"],
                "container": container_bg,
            }
        )
        self._draw()

    def _rounded(self, color):
        w, h, r = self.width, self.height, self.radius
        self.create_arc(0, 0, 2 * r, 2 * r, start=90, extent=90, fill=color, outline=color)
        self.create_arc(w - 2 * r, 0, w, 2 * r, start=0, extent=90, fill=color, outline=color)
        self.create_arc(0, h - 2 * r, 2 * r, h, start=180, extent=90, fill=color, outline=color)
        self.create_arc(w - 2 * r, h - 2 * r, w, h, start=270, extent=90, fill=color, outline=color)
        self.create_rectangle(r, 0, w - r, h, fill=color, outline=color)
        self.create_rectangle(0, r, w, h - r, fill=color, outline=color)

    def _draw(self):
        self.delete("all")
        self.configure(bg=self.colors["container"])
        color = self.colors["disabled"] if not self.enabled else (self.colors["press"] if self.pressed else self.colors["bg"])
        self._rounded(color)
        self.create_text(self.width // 2, self.height // 2, text=self.text, fill=self.colors["fg"], font=("Adwaita Sans", 10, "bold"))

    def _on_enter(self, _event):
        if self.enabled and not self.pressed:
            self.delete("all")
            self.configure(bg=self.colors["container"])
            self._rounded(self.colors["hover"])
            self.create_text(self.width // 2, self.height // 2, text=self.text, fill=self.colors["fg"], font=("Adwaita Sans", 10, "bold"))

    def _on_leave(self, _event):
        self.pressed = False
        self._draw()

    def _on_press(self, _event):
        if not self.enabled:
            return
        self.pressed = True
        self._draw()

    def _on_release(self, _event):
        if not self.enabled:
            return
        run = self.pressed
        self.pressed = False
        self._draw()
        if run:
            self.command()

    def set_enabled(self, enabled: bool):
        self.enabled = enabled
        self.configure(cursor="hand2" if enabled else "arrow")
        self._draw()


class OpsConsole:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Ops Console")
        self.root.geometry("1180x760")
        self.root.minsize(980, 640)

        self.settings = load_settings()
        self.theme_var = tk.StringVar(value=self.settings.get("theme", "dark"))
        self.refresh_var = tk.IntVar(value=self.settings.get("refresh_interval_ms", 1200))
        self.system_manager = "none"

        self.conn_rows = []

        self._build_ui()
        self.apply_theme(self.theme_var.get())
        self._refresh_connections_once()
        self._schedule_connections_refresh()
        self.refresh_updates()

    def _build_ui(self):
        self.style = ttk.Style()
        self.style.theme_use("clam")

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        header = tk.Frame(self.root, padx=14, pady=12)
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(1, weight=1)

        self.title = tk.Label(header, text="Ops Console", font=("Adwaita Sans", 22, "bold"))
        self.title.grid(row=0, column=0, sticky="w")
        self.subtitle = tk.Label(header, text="Network Forensics + Update Orchestrator", font=("Adwaita Sans", 10))
        self.subtitle.grid(row=1, column=0, sticky="w", pady=(2, 0))

        self.theme_box = ttk.Combobox(header, textvariable=self.theme_var, values=("dark", "light"), state="readonly", width=10, style="App.TCombobox")
        self.theme_box.grid(row=0, column=2, rowspan=2, sticky="e")
        self.theme_box.bind("<<ComboboxSelected>>", lambda _e: self.apply_theme(self.theme_var.get()))

        self.tabs = ttk.Notebook(self.root)
        self.tabs.grid(row=1, column=0, sticky="nsew", padx=14, pady=(0, 12))

        self._build_network_tab()
        self._build_updates_tab()

        self.status_var = tk.StringVar(value="Ready")
        self.status = tk.Label(self.root, textvariable=self.status_var, anchor="w", padx=14, pady=8, font=("Adwaita Sans", 10))
        self.status.grid(row=2, column=0, sticky="ew")

    def _build_network_tab(self):
        tab = tk.Frame(self.tabs)
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(1, weight=1)
        self.tabs.add(tab, text="Network")

        controls = tk.Frame(tab, padx=12, pady=10)
        controls.grid(row=0, column=0, sticky="ew")

        self.btn_refresh_conn = RoundedButton(controls, "Refresh", self._refresh_connections_once, width=90)
        self.btn_refresh_conn.pack(side="left")

        tk.Label(controls, text="Interval (ms)", font=("Adwaita Sans", 10, "bold")).pack(side="left", padx=(12, 6))
        self.refresh_spin = ttk.Spinbox(controls, from_=300, to=5000, increment=100, textvariable=self.refresh_var, width=7, style="App.TSpinbox", command=self._on_refresh_interval)
        self.refresh_spin.pack(side="left")
        self.refresh_spin.bind("<Return>", lambda _e: self._on_refresh_interval())

        frame = tk.Frame(tab, padx=12, pady=0)
        frame.grid(row=1, column=0, sticky="nsew")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

        self.conn_tree = ttk.Treeview(frame, columns=("flag", "process", "pid", "local", "remote", "status"), show="headings", style="App.Treeview")
        for col, title, width in (
            ("flag", "Alert", 70),
            ("process", "Process", 220),
            ("pid", "PID", 70),
            ("local", "Local", 210),
            ("remote", "Remote", 280),
            ("status", "State", 110),
        ):
            self.conn_tree.heading(col, text=title)
            self.conn_tree.column(col, width=width, anchor="w")
        self.conn_tree.grid(row=0, column=0, sticky="nsew")
        self.conn_tree.bind("<Double-1>", self._on_connection_double_click)

        s = ttk.Scrollbar(frame, orient="vertical", command=self.conn_tree.yview)
        self.conn_tree.configure(yscrollcommand=s.set)
        s.grid(row=0, column=1, sticky="ns")

    def _build_updates_tab(self):
        tab = tk.Frame(self.tabs)
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(1, weight=1)
        self.tabs.add(tab, text="Updates")

        controls = tk.Frame(tab, padx=12, pady=10)
        controls.grid(row=0, column=0, sticky="ew")

        self.btn_refresh_upd = RoundedButton(controls, "Check Updates", self.refresh_updates, width=128)
        self.btn_refresh_upd.pack(side="left")

        self.btn_run_system = RoundedButton(controls, "Run System Update", self._run_system_update, width=168)
        self.btn_run_system.pack(side="left", padx=(8, 0))

        self.btn_run_flatpak = RoundedButton(controls, "Run Flatpak Update", self._run_flatpak_update, width=170)
        self.btn_run_flatpak.pack(side="left", padx=(8, 0))

        self.detected_label = tk.Label(controls, text="Managers: -", font=("Adwaita Sans", 10))
        self.detected_label.pack(side="left", padx=(12, 0))

        frame = tk.Frame(tab, padx=12, pady=0)
        frame.grid(row=1, column=0, sticky="nsew")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

        self.update_text = tk.Text(frame, wrap="word", font=("Adwaita Mono", 10), state="disabled")
        self.update_text.grid(row=0, column=0, sticky="nsew")

        s = ttk.Scrollbar(frame, orient="vertical", command=self.update_text.yview)
        self.update_text.configure(yscrollcommand=s.set)
        s.grid(row=0, column=1, sticky="ns")

    def _on_refresh_interval(self):
        try:
            value = int(self.refresh_var.get())
        except Exception:  # noqa: BLE001
            value = 1200
        value = max(300, min(5000, value))
        self.refresh_var.set(value)
        self.settings["refresh_interval_ms"] = value
        save_settings(self.settings)
        self.status_var.set(f"Refresh interval set to {value} ms")

    def _schedule_connections_refresh(self):
        self._refresh_connections_once(set_status=False)
        self.root.after(int(self.refresh_var.get()), self._schedule_connections_refresh)

    def _refresh_connections_once(self, set_status: bool = True):
        known = self.settings.get("known_processes", [])
        rows = collect_connections(known)
        self.conn_rows = rows

        current = set(self.conn_tree.get_children())
        row_ids = set()
        for i, r in enumerate(rows):
            row_id = f"row-{i}"
            row_ids.add(row_id)
            values = (
                "!" if r.suspicious else "",
                r.process,
                str(r.pid),
                r.laddr,
                r.raddr,
                r.status,
            )
            if row_id in current:
                self.conn_tree.item(row_id, values=values)
            else:
                self.conn_tree.insert("", "end", iid=row_id, values=values)

        for orphan in current - row_ids:
            self.conn_tree.delete(orphan)

        if set_status:
            alerts = sum(1 for r in rows if r.suspicious)
            self.status_var.set(f"Connections: {len(rows)} | Alerts: {alerts}")

    def _on_connection_double_click(self, _event):
        selected = self.conn_tree.selection()
        if not selected:
            return
        item = self.conn_tree.item(selected[0], "values")
        remote = item[4]
        if remote == "-":
            messagebox.showinfo("Connection", "No remote address for this socket.")
            return
        host = remote.split(":", 1)[0]
        dns = reverse_dns(host)
        messagebox.showinfo("Reverse DNS", f"IP: {host}\nHost: {dns}")

    def refresh_updates(self):
        managers = detect_managers()
        self.detected_label.configure(text=f"Managers: {', '.join(managers) if managers else 'none'}")
        self.system_manager = "pacman" if "pacman" in managers else ("apt" if "apt" in managers else "none")
        can_launch, reason = can_launch_updates_from_app()
        self.btn_run_system.set_enabled(can_launch and self.system_manager != "none")
        self.btn_run_flatpak.set_enabled(can_launch and ("flatpak" in managers))
        if not can_launch:
            self.status_var.set(reason)

        def task():
            results = check_all_updates()
            self.root.after(0, lambda: self._render_updates(results))

        threading.Thread(target=task, daemon=True).start()

    def _run_system_update(self):
        if self.system_manager == "none":
            messagebox.showinfo("System Update", "No supported system package manager detected (pacman/apt).")
            return
        ok, info = run_update_in_terminal(self.system_manager)
        if ok:
            self.status_var.set(info)
            return
        self.status_var.set("Failed to launch system update")
        messagebox.showerror("System Update", info)

    def _run_flatpak_update(self):
        managers = detect_managers()
        if "flatpak" not in managers:
            messagebox.showinfo("Flatpak Update", "Flatpak is not available on this system.")
            return
        ok, info = run_update_in_terminal("flatpak")
        if ok:
            self.status_var.set(info)
            return
        self.status_var.set("Failed to launch Flatpak update")
        messagebox.showerror("Flatpak Update", info)

    def _render_updates(self, results):
        lines = []
        for r in results:
            lines.append(f"[{r.manager}] {r.summary}")
            lines.append(f"Command: {r.command}")
            if r.details:
                lines.append(r.details)
            lines.append("-" * 50)

        text = "\n".join(lines) if lines else "No supported managers detected."
        self.update_text.configure(state="normal")
        self.update_text.delete("1.0", tk.END)
        self.update_text.insert("1.0", text)
        self.update_text.configure(state="disabled")
        self.status_var.set("Update check finished")

    def apply_theme(self, theme_name: str):
        if theme_name not in THEMES:
            theme_name = "dark"
        self.theme_var.set(theme_name)
        self.settings["theme"] = theme_name
        save_settings(self.settings)

        p = THEMES[theme_name]
        self.style.configure("App.TCombobox", fieldbackground=p["entry"], foreground=p["entry_fg"], bordercolor=p["line"], padding=4, font=("Adwaita Sans", 10))
        self.style.map("App.TCombobox", fieldbackground=[("readonly", p["entry"])], foreground=[("readonly", p["entry_fg"])])
        self.style.configure("App.TSpinbox", fieldbackground=p["entry"], foreground=p["entry_fg"], bordercolor=p["line"], padding=4, font=("Adwaita Sans", 10))
        self.style.configure("App.Treeview", background=p["card"], fieldbackground=p["card"], foreground=p["text"], rowheight=28, borderwidth=0, font=("Adwaita Sans", 10))
        self.style.map("App.Treeview", background=[("selected", p["select"])], foreground=[("selected", p["text"])])

        self.root.configure(bg=p["root"])
        self.title.configure(bg=p["root"], fg=p["text"])
        self.subtitle.configure(bg=p["root"], fg=p["muted"])
        self.detected_label.configure(bg=p["panel"], fg=p["muted"])
        self.status.configure(bg=p["root"], fg=p["muted"])

        for btn in (self.btn_refresh_conn, self.btn_refresh_upd, self.btn_run_system, self.btn_run_flatpak):
            btn.configure_theme(p, btn.master.cget("bg"))

        self.update_text.configure(bg=p["card"], fg=p["text"], insertbackground=p["text"]) 
