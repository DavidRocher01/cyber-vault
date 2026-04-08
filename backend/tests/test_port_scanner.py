"""
Unit tests — scanner.port_scanner
Covers: nmap unavailable, open ports detection, critical port detection.
"""

import sys
import types
import pytest
from unittest.mock import MagicMock, patch


# ── helpers ───────────────────────────────────────────────────────────────────

def _make_nmap_module(host: str, open_ports: list[int]):
    """Build a fake nmap module that reports given open ports."""
    nm_instance = MagicMock()
    nm_instance.all_hosts.return_value = [host]
    nm_instance.__getitem__ = lambda self, h: {
        "tcp": {p: {"state": "open"} for p in open_ports}
    }
    scanner_cls = MagicMock(return_value=nm_instance)
    nmap_mod = types.ModuleType("nmap")
    nmap_mod.PortScanner = scanner_cls
    nmap_mod.PortScannerError = Exception
    return nmap_mod


# ── tests ─────────────────────────────────────────────────────────────────────

def test_scan_ports_nmap_unavailable():
    """When nmap is not installed the result contains an error and CRITICAL status."""
    with patch.dict(sys.modules, {"nmap": None}):
        # Force reimport with nmap absent
        if "scanner.port_scanner" in sys.modules:
            del sys.modules["scanner.port_scanner"]
        from scanner.port_scanner import scan_ports
        result = scan_ports("example.com")
    assert result["status"] == "CRITICAL"
    assert result["error"] is not None


def test_scan_ports_no_open_ports():
    """No open sensitive ports → status OK."""
    fake_nmap = _make_nmap_module("example.com", open_ports=[])
    with patch.dict(sys.modules, {"nmap": fake_nmap}):
        if "scanner.port_scanner" in sys.modules:
            del sys.modules["scanner.port_scanner"]
        from scanner.port_scanner import scan_ports
        result = scan_ports("example.com")
    assert result["status"] == "OK"
    assert result["open_ports"] == []
    assert result["critical_ports"] == []


def test_scan_ports_critical_port_detected():
    """A critical open port (e.g. 5432 PostgreSQL) → status WARNING or CRITICAL."""
    fake_nmap = _make_nmap_module("example.com", open_ports=[5432])
    with patch.dict(sys.modules, {"nmap": fake_nmap}):
        if "scanner.port_scanner" in sys.modules:
            del sys.modules["scanner.port_scanner"]
        from scanner.port_scanner import scan_ports
        result = scan_ports("example.com")
    assert result["status"] in ("WARNING", "CRITICAL")
    assert 5432 in result["critical_ports"]


def test_scan_ports_returns_required_keys():
    """Result dict always contains the expected keys."""
    fake_nmap = _make_nmap_module("example.com", open_ports=[])
    with patch.dict(sys.modules, {"nmap": fake_nmap}):
        if "scanner.port_scanner" in sys.modules:
            del sys.modules["scanner.port_scanner"]
        from scanner.port_scanner import scan_ports
        result = scan_ports("example.com")
    assert {"open_ports", "critical_ports", "status", "error"} <= result.keys()
