import socket
from dataclasses import dataclass

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
    status: str
    suspicious: bool


def _safe_process_name(pid: int) -> str:
    if psutil is None:
        return "unknown"
    try:
        return psutil.Process(pid).name()
    except Exception:  # noqa: BLE001
        return "unknown"


def _is_private_ip(host: str) -> bool:
    if not host:
        return True
    return host.startswith("10.") or host.startswith("192.168.") or host.startswith("172.16.") or host.startswith("127.")


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

        process = _safe_process_name(c.pid)
        suspicious = _is_suspicious(c.status, remote_host, process, known)

        out.append(
            ConnectionRow(
                pid=c.pid,
                process=process,
                laddr=local,
                raddr=remote,
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
