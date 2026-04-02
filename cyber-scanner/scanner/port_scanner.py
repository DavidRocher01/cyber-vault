from typing import Any

from scanner.constants import SENSITIVE_PORTS, CRITICAL_PORTS

try:
    import nmap  # type: ignore
    NMAP_AVAILABLE = True
except ImportError:
    NMAP_AVAILABLE = False


def scan_ports(host: str) -> dict[str, Any]:
    """
    Scan sensitive ports on the given host using nmap.

    Args:
        host: The hostname or IP address to scan

    Returns:
        A dict with keys: open_ports, critical_ports, status, error
    """
    result: dict[str, Any] = {
        "open_ports": [],
        "critical_ports": [],
        "status": "CRITICAL",
        "error": None,
    }

    if not NMAP_AVAILABLE:
        result["error"] = "python-nmap is not installed. Run: pip install python-nmap"
        result["status"] = "CRITICAL"
        return result

    try:
        nm = nmap.PortScanner()
        ports_arg: str = ",".join(str(p) for p in SENSITIVE_PORTS)
        nm.scan(hosts=host, ports=ports_arg, arguments="-T4 --open")

        open_ports: list[int] = []
        found_critical: list[int] = []

        for scanned_host in nm.all_hosts():
            if "tcp" in nm[scanned_host]:
                for port, port_info in nm[scanned_host]["tcp"].items():
                    if port_info.get("state") == "open":
                        open_ports.append(port)
                        if port in CRITICAL_PORTS:
                            found_critical.append(port)

        open_ports.sort()
        found_critical.sort()

        result["open_ports"] = open_ports
        result["critical_ports"] = found_critical

        critical_count: int = len(found_critical)
        if critical_count == 0:
            result["status"] = "OK"
        elif critical_count == 1:
            result["status"] = "WARNING"
        else:
            result["status"] = "CRITICAL"

    except nmap.PortScannerError as e:
        error_msg: str = str(e)
        if "nmap programme was not found" in error_msg or "nmap" in error_msg.lower():
            result["error"] = "nmap is not installed on this system. Install it from https://nmap.org"
        else:
            result["error"] = f"nmap error: {error_msg}"
        result["status"] = "CRITICAL"
    except Exception as e:
        result["error"] = f"Unexpected error during port scan: {e}"
        result["status"] = "CRITICAL"

    return result
