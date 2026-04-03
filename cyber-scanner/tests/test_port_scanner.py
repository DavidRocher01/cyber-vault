"""
Tests for scanner.port_scanner.scan_ports()
All network/nmap calls are mocked — no real connections are made.
"""

from unittest.mock import patch, MagicMock

import pytest

from scanner.port_scanner import scan_ports
from scanner.constants import CRITICAL_PORTS


# ---------------------------------------------------------------------------
# Tests — return shape
# ---------------------------------------------------------------------------

class TestScanPortsReturnShape:
    def test_returns_expected_keys_when_nmap_unavailable(self):
        with patch("scanner.port_scanner.NMAP_AVAILABLE", False):
            result = scan_ports("example.com")

        expected_keys = {"open_ports", "critical_ports", "status", "error"}
        assert set(result.keys()) == expected_keys

    def test_returns_expected_keys_on_successful_scan(self):
        mock_nm = MagicMock()
        mock_nm.all_hosts.return_value = []

        with patch("scanner.port_scanner.NMAP_AVAILABLE", True), \
             patch("nmap.PortScanner", return_value=mock_nm):
            result = scan_ports("example.com")

        expected_keys = {"open_ports", "critical_ports", "status", "error"}
        assert set(result.keys()) == expected_keys


# ---------------------------------------------------------------------------
# Tests — nmap not available
# ---------------------------------------------------------------------------

class TestScanPortsNmapUnavailable:
    def test_nmap_not_available_sets_error(self):
        with patch("scanner.port_scanner.NMAP_AVAILABLE", False):
            result = scan_ports("example.com")

        assert result["error"] is not None
        assert "python-nmap" in result["error"]
        assert result["status"] == "CRITICAL"
        assert result["open_ports"] == []
        assert result["critical_ports"] == []


# ---------------------------------------------------------------------------
# Tests — scan results
# ---------------------------------------------------------------------------

class TestScanPortsResults:
    def _make_scanner(self, open_ports: list[int]) -> MagicMock:
        """Build a mock nmap.PortScanner that reports the given ports as open."""
        tcp_data = {port: {"state": "open"} for port in open_ports}

        host_mock = MagicMock()
        host_mock.__contains__ = lambda self, item: item == "tcp"
        host_mock.__getitem__ = lambda self, item: tcp_data if item == "tcp" else {}

        nm = MagicMock()
        nm.all_hosts.return_value = ["192.168.1.1"]
        nm.__getitem__ = lambda self, key: host_mock
        return nm

    def test_no_open_ports_status_ok(self):
        mock_nm = MagicMock()
        mock_nm.all_hosts.return_value = []

        with patch("scanner.port_scanner.NMAP_AVAILABLE", True), \
             patch("nmap.PortScanner", return_value=mock_nm):
            result = scan_ports("example.com")

        assert result["open_ports"] == []
        assert result["critical_ports"] == []
        assert result["status"] == "OK"
        assert result["error"] is None

    def test_one_critical_port_open_status_warning(self):
        critical_port = next(iter(CRITICAL_PORTS))  # e.g. 3306
        mock_nm = self._make_scanner([critical_port])

        with patch("scanner.port_scanner.NMAP_AVAILABLE", True), \
             patch("nmap.PortScanner", return_value=mock_nm):
            result = scan_ports("example.com")

        assert critical_port in result["open_ports"]
        assert critical_port in result["critical_ports"]
        assert result["status"] == "WARNING"

    def test_two_critical_ports_open_status_critical(self):
        two_critical = list(CRITICAL_PORTS)[:2]
        mock_nm = self._make_scanner(two_critical)

        with patch("scanner.port_scanner.NMAP_AVAILABLE", True), \
             patch("nmap.PortScanner", return_value=mock_nm):
            result = scan_ports("example.com")

        assert result["status"] == "CRITICAL"
        assert len(result["critical_ports"]) >= 2

    def test_non_critical_port_open_does_not_escalate(self):
        # Port 22 (SSH) is in SENSITIVE_PORTS but NOT in CRITICAL_PORTS
        mock_nm = self._make_scanner([22])

        with patch("scanner.port_scanner.NMAP_AVAILABLE", True), \
             patch("nmap.PortScanner", return_value=mock_nm):
            result = scan_ports("example.com")

        assert 22 in result["open_ports"]
        assert 22 not in result["critical_ports"]
        assert result["status"] == "OK"

    def test_nmap_scanner_error_sets_error(self):
        import nmap as nmap_module

        mock_nm = MagicMock()
        mock_nm.scan.side_effect = nmap_module.PortScannerError("nmap programme was not found")

        with patch("scanner.port_scanner.NMAP_AVAILABLE", True), \
             patch("nmap.PortScanner", return_value=mock_nm):
            result = scan_ports("example.com")

        assert result["error"] is not None
        assert result["status"] == "CRITICAL"

    def test_open_ports_are_sorted(self):
        mock_nm = self._make_scanner([5432, 21, 3306])

        with patch("scanner.port_scanner.NMAP_AVAILABLE", True), \
             patch("nmap.PortScanner", return_value=mock_nm):
            result = scan_ports("example.com")

        assert result["open_ports"] == sorted(result["open_ports"])
        assert result["critical_ports"] == sorted(result["critical_ports"])
