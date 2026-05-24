import socket
from dataclasses import dataclass
from ipaddress import ip_address

try:
    import psutil  # type: ignore
except Exception:  # noqa: BLE001
    psutil = None


@dataclass
class ConnectionRow:
    pid: int
    process: str
    laddr: str
    raddr: str
    remote_host: str
    username: str
    exe: str
    cmdline: str
    status: str
    suspicious: bool


def _safe_process_info(pid: int) -> tuple[str, str, str, str]:
    if psutil is None:
        return "unknown", "-", "-", "-"
    try:
        proc = psutil.Process(pid)
    except Exception:  # noqa: BLE001
        return "unknown", "-", "-", "-"

    try:
        name = proc.name()
    except Exception:  # noqa: BLE001
        name = "unknown"

    try:
        username = proc.username()
    except Exception:  # noqa: BLE001
        username = "-"

    try:
        exe = proc.exe()
    except Exception:  # noqa: BLE001
        exe = "-"

    try:
        cmdline = " ".join(proc.cmdline())
    except Exception:  # noqa: BLE001
        cmdline = "-"

    return name, username, exe, cmdline


def _is_private_ip(host: str) -> bool:
    if not host:
        return True
    try:
        addr = ip_address(host)
    except ValueError:
        return True
    return addr.is_private or addr.is_loopback or addr.is_link_local


def _is_suspicious(status: str, host: str, process: str, known: set[str]) -> bool:
    if status != "ESTABLISHED":
        return False
    proc = process.lower()
    unknown_proc = proc not in known
    external = not _is_private_ip(host)
    return unknown_proc and external


def collect_connections(known_processes: list[str]) -> list[ConnectionRow]:
    if psutil is None:
        return []

    known = {p.lower() for p in known_processes}
    out: list[ConnectionRow] = []

    try:
        conns = psutil.net_connections(kind="inet")
    except Exception:  # noqa: BLE001
        return out

    for c in conns:
        if c.pid is None:
            continue
        if not c.laddr:
            continue

        local = f"{c.laddr.ip}:{c.laddr.port}"
        if c.raddr:
            remote_host = c.raddr.ip
            remote = f"{c.raddr.ip}:{c.raddr.port}"
        else:
            remote_host = ""
            remote = "-"

        process, username, exe, cmdline = _safe_process_info(c.pid)
        suspicious = _is_suspicious(c.status, remote_host, process, known)

        out.append(
            ConnectionRow(
                pid=c.pid,
                process=process,
                laddr=local,
                raddr=remote,
                remote_host=remote_host,
                username=username,
                exe=exe,
                cmdline=cmdline,
                status=c.status,
                suspicious=suspicious,
            )
        )

    out.sort(key=lambda r: (not r.suspicious, r.process.lower(), r.pid))
    return out


def reverse_dns(ip: str) -> str:
    try:
        host, _alias, _ips = socket.gethostbyaddr(ip)
        return host
    except Exception:  # noqa: BLE001
        return "N/A"
