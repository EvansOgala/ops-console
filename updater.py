import shutil
import subprocess
from pathlib import Path
from dataclasses import dataclass


@dataclass
class UpdateResult:
    manager: str
    available: bool
    summary: str
    details: str
    command: str


def _run(cmd: list[str]) -> tuple[int, str]:
    try:
        c = subprocess.run(cmd, text=True, capture_output=True, timeout=60)
    except Exception as exc:  # noqa: BLE001
        return 1, str(exc)
    out = (c.stdout or "") + (c.stderr or "")
    return c.returncode, out.strip()


def detect_managers() -> list[str]:
    managers = []
    if shutil.which("pacman"):
        managers.append("pacman")
    if shutil.which("flatpak"):
        managers.append("flatpak")
    if shutil.which("apt"):
        managers.append("apt")
    return managers


def check_pacman() -> UpdateResult:
    cmd = ["checkupdates"] if shutil.which("checkupdates") else ["pacman", "-Qu"]
    code, out = _run(cmd)
    lines = [l for l in out.splitlines() if l.strip()]
    if code not in (0, 2):
        return UpdateResult("pacman", False, "Check failed", out or "No output", " ".join(cmd))
    return UpdateResult("pacman", bool(lines), f"{len(lines)} updates" if lines else "Up to date", "\n".join(lines[:200]), " ".join(cmd))


def check_flatpak() -> UpdateResult:
    cmd = ["flatpak", "remote-ls", "--updates"]
    code, out = _run(cmd)
    if code != 0:
        return UpdateResult("flatpak", False, "Check failed", out or "No output", " ".join(cmd))
    lines = [l for l in out.splitlines() if l.strip()]
    return UpdateResult("flatpak", bool(lines), f"{len(lines)} updates" if lines else "Up to date", "\n".join(lines[:200]), " ".join(cmd))


def check_apt() -> UpdateResult:
    cmd = ["apt", "list", "--upgradable"]
    code, out = _run(cmd)
    if code != 0:
        return UpdateResult("apt", False, "Check failed", out or "No output", " ".join(cmd))
    lines = [l for l in out.splitlines() if l.strip() and not l.startswith("Listing")]
    return UpdateResult("apt", bool(lines), f"{len(lines)} updates" if lines else "Up to date", "\n".join(lines[:200]), " ".join(cmd))


def check_all_updates() -> list[UpdateResult]:
    out: list[UpdateResult] = []
    managers = detect_managers()
    for m in managers:
        if m == "pacman":
            out.append(check_pacman())
        elif m == "flatpak":
            out.append(check_flatpak())
        elif m == "apt":
            out.append(check_apt())
    return out


def _in_flatpak() -> bool:
    return bool(Path("/.flatpak-info").exists())


def can_launch_updates_from_app() -> tuple[bool, str]:
    if not _in_flatpak():
        return True, ""
    if shutil.which("flatpak-spawn"):
        return True, ""
    return False, "Host command launch unavailable: flatpak-spawn is missing on this system."


def _host_has_command(command: str) -> bool:
    if not shutil.which("flatpak-spawn"):
        return False
    probe = subprocess.run(
        ["flatpak-spawn", "--host", "sh", "-lc", f"command -v {command} >/dev/null 2>&1"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    return probe.returncode == 0


def _build_update_shell_command(manager: str) -> str:
    if manager == "pacman":
        base = "sudo pacman -Syu"
    elif manager == "flatpak":
        base = "flatpak update"
    elif manager == "apt":
        base = "sudo apt update && sudo apt upgrade"
    else:
        raise ValueError(f"Unsupported manager: {manager}")

    return (
        f"{base}; status=$?; echo; "
        "if [ $status -eq 0 ]; then echo Update finished.; "
        "else echo Update failed with exit code $status.; fi; "
        "echo; read -r -p 'Press Enter to close...' _"
    )


def run_update_in_terminal(manager: str) -> tuple[bool, str]:
    if manager not in {"pacman", "flatpak", "apt"}:
        return False, f"Unsupported update manager: {manager}"

    shell_cmd = _build_update_shell_command(manager)
    terminal_choices = [
        ("x-terminal-emulator", ["x-terminal-emulator", "-e", "bash", "-lc", shell_cmd]),
        ("gnome-terminal", ["gnome-terminal", "--", "bash", "-lc", shell_cmd]),
        ("konsole", ["konsole", "-e", "bash", "-lc", shell_cmd]),
        ("xfce4-terminal", ["xfce4-terminal", "-x", "bash", "-lc", shell_cmd]),
        ("kitty", ["kitty", "bash", "-lc", shell_cmd]),
        ("alacritty", ["alacritty", "-e", "bash", "-lc", shell_cmd]),
        ("xterm", ["xterm", "-e", "bash", "-lc", shell_cmd]),
    ]

    if _in_flatpak():
        if not shutil.which("flatpak-spawn"):
            return False, "flatpak-spawn is not available in this sandbox."
        for term_name, term_cmd in terminal_choices:
            if not _host_has_command(term_name):
                continue
            try:
                subprocess.Popen(["flatpak-spawn", "--host", *term_cmd])
                return True, f"Launched {manager} update in host terminal."
            except OSError:
                continue
        return False, "No supported host terminal found (x-terminal-emulator, gnome-terminal, konsole, xfce4-terminal, kitty, alacritty, xterm)."

    for term_name, term_cmd in terminal_choices:
        if shutil.which(term_name) is None:
            continue
        try:
            subprocess.Popen(term_cmd)
            return True, f"Launched {manager} update in terminal."
        except OSError:
            continue

    return False, "No supported terminal found (x-terminal-emulator, gnome-terminal, konsole, xfce4-terminal, kitty, alacritty, xterm)."
