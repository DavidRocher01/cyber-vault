import ssl
import socket
from datetime import datetime, timezone
from typing import Any


def check_ssl(hostname: str) -> dict[str, Any]:
    """
    Check SSL/TLS certificate information for a given hostname.

    Args:
        hostname: The hostname to check (e.g. "example.com")

    Returns:
        A dict with keys: valid, expiry_date, days_remaining, protocol, tls_ok, status, error
    """
    result: dict[str, Any] = {
        "valid": False,
        "expiry_date": None,
        "days_remaining": None,
        "protocol": None,
        "tls_ok": False,
        "status": "CRITICAL",
        "error": None,
    }

    try:
        context = ssl.create_default_context()

        with socket.create_connection((hostname, 443), timeout=10) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert = ssock.getpeercert()
                protocol = ssock.version()

                # Parse expiry date from certificate
                # Format: 'Nov 15 12:00:00 2025 GMT'
                not_after_str: str = cert["notAfter"]
                not_after: datetime = datetime.strptime(not_after_str, "%b %d %H:%M:%S %Y %Z")
                now: datetime = datetime.now(timezone.utc).replace(tzinfo=None)
                days_remaining: int = (not_after - now).days

                result["valid"] = True
                result["expiry_date"] = not_after.strftime("%d/%m/%Y")
                result["days_remaining"] = days_remaining
                result["protocol"] = protocol if protocol else "Unknown"

                # TLS 1.2 or higher is acceptable
                tls_ok: bool = protocol in ("TLSv1.2", "TLSv1.3")
                result["tls_ok"] = tls_ok

                # Determine status based on days remaining
                if days_remaining < 0:
                    result["status"] = "CRITICAL"
                elif days_remaining < 7:
                    result["status"] = "CRITICAL"
                elif days_remaining < 30:
                    result["status"] = "WARNING"
                else:
                    result["status"] = "OK"

                # Bad TLS version overrides to CRITICAL regardless of cert validity
                if not tls_ok:
                    result["status"] = "CRITICAL"

    except ssl.SSLCertVerificationError as e:
        result["error"] = f"Certificate verification failed: {e}"
        result["status"] = "CRITICAL"
    except ssl.SSLError as e:
        result["error"] = f"SSL error: {e}"
        result["status"] = "CRITICAL"
    except socket.timeout:
        result["error"] = "Connection timed out"
        result["status"] = "CRITICAL"
    except socket.gaierror as e:
        result["error"] = f"DNS resolution failed: {e}"
        result["status"] = "CRITICAL"
    except ConnectionRefusedError:
        result["error"] = "Connection refused on port 443"
        result["status"] = "CRITICAL"
    except Exception as e:
        result["error"] = f"Unexpected error: {e}"
        result["status"] = "CRITICAL"

    return result
