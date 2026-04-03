import argparse
from typing import Any
from urllib.parse import urlparse

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

from scanner.ssl_checker import check_ssl
from scanner.headers_checker import check_headers
from scanner.port_scanner import scan_ports
from scanner.sca_checker import check_sca
from scanner.secrets_checker import check_secrets
from scanner.remediation import generate_remediation
from scanner.report_generator import generate_report
from scanner.constants import PORT_NAMES
from scanner.email_checker import check_email_security
from scanner.cookie_checker import check_cookies
from scanner.cors_checker import check_cors
from scanner.ip_reputation import check_ip_reputation
from scanner.dns_scanner import scan_subdomains
from scanner.cms_detector import detect_cms
from scanner.breach_checker import check_breach
from scanner.waf_detector import detect_waf
from scanner.tech_fingerprint import fingerprint_tech
from scanner.tls_auditor import audit_tls
from scanner.subdomain_takeover import check_subdomain_takeover
from scanner.threat_intel import get_threat_intel
from scanner.http_methods import check_http_methods
from scanner.open_redirect import check_open_redirect
from scanner.clickjacking import check_clickjacking
from scanner.directory_listing import check_directory_listing
from scanner.robots_sitemap import analyse_robots_sitemap
from scanner.jwt_checker import check_jwt

console = Console()

STATUS_COLORS: dict[str, str] = {
    "OK": "green",
    "WARNING": "yellow",
    "CRITICAL": "red",
}


def colorize_status(status: str) -> str:
    color = STATUS_COLORS.get(status, "white")
    return f"[{color}]{status}[/{color}]"


def extract_hostname(url: str) -> str:
    """Extract clean hostname from a URL."""
    parsed = urlparse(url)
    # If no scheme, urlparse puts everything in path
    if not parsed.scheme:
        parsed = urlparse(f"https://{url}")
    hostname = parsed.hostname or url
    return hostname


def get_overall_status(statuses: list[str]) -> str:
    """Determine overall risk level from a list of statuses."""
    if "CRITICAL" in statuses:
        return "CRITICAL"
    elif "WARNING" in statuses:
        return "WARNING"
    return "OK"


def display_banner() -> None:
    console.print(
        Panel.fit(
            "[bold cyan]CYBER-SCANNER v1.0[/bold cyan]\n"
            "[dim]External Attack Surface Scanner[/dim]",
            border_style="cyan",
        )
    )
    console.print()


def display_ssl_results(ssl_result: dict[str, Any], hostname: str) -> str:
    console.print("[bold white]SSL / TLS Certificate[/bold white]")

    table = Table(box=box.ROUNDED, show_header=True, header_style="bold magenta")
    table.add_column("Property", style="dim", width=22)
    table.add_column("Value")

    if ssl_result.get("error"):
        table.add_row("Status", colorize_status("CRITICAL"))
        table.add_row("Error", f"[red]{ssl_result['error']}[/red]")
    else:
        status = ssl_result["status"]
        table.add_row("Status", colorize_status(status))
        table.add_row("Valid", "[green]Yes[/green]" if ssl_result["valid"] else "[red]No[/red]")
        table.add_row("Expiry Date", str(ssl_result["expiry_date"]))
        days = ssl_result["days_remaining"]
        days_color = "green" if days >= 30 else ("yellow" if days >= 7 else "red")
        table.add_row("Days Remaining", f"[{days_color}]{days}[/{days_color}]")
        table.add_row("Protocol", str(ssl_result["protocol"]))
        tls_ok = ssl_result["tls_ok"]
        table.add_row(
            "TLS OK",
            "[green]Yes (>= TLS 1.2)[/green]" if tls_ok else "[red]No (outdated protocol)[/red]",
        )

    console.print(table)
    console.print()
    return ssl_result["status"]


def display_headers_results(headers_result: dict[str, Any]) -> str:
    console.print("[bold white]HTTP Security Headers[/bold white]")

    table = Table(box=box.ROUNDED, show_header=True, header_style="bold magenta")
    table.add_column("Property", style="dim", width=22)
    table.add_column("Value")

    if headers_result.get("error"):
        table.add_row("Status", colorize_status("CRITICAL"))
        table.add_row("Error", f"[red]{headers_result['error']}[/red]")
    else:
        status = headers_result["status"]
        score = headers_result["score"]
        table.add_row("Status", colorize_status(status))
        table.add_row("HTTP Status Code", str(headers_result["status_code"]))
        score_color = "green" if score == 6 else ("yellow" if score >= 4 else "red")
        table.add_row("Score", f"[{score_color}]{score}/6[/{score_color}]")

        if headers_result["headers_found"]:
            found_str = "\n".join(f"[green]+ {h}[/green]" for h in headers_result["headers_found"])
            table.add_row("Headers Present", found_str)

        if headers_result["headers_missing"]:
            missing_str = "\n".join(f"[red]- {h}[/red]" for h in headers_result["headers_missing"])
            table.add_row("Headers Missing", missing_str)

    console.print(table)
    console.print()
    return headers_result["status"]


def display_ports_results(ports_result: dict[str, Any]) -> str:
    console.print("[bold white]Port Scan[/bold white]")

    table = Table(box=box.ROUNDED, show_header=True, header_style="bold magenta")
    table.add_column("Property", style="dim", width=22)
    table.add_column("Value")

    if ports_result.get("error"):
        table.add_row("Status", colorize_status("CRITICAL"))
        table.add_row("Error", f"[red]{ports_result['error']}[/red]")
    else:
        status = ports_result["status"]
        table.add_row("Status", colorize_status(status))

        open_ports = ports_result["open_ports"]
        if open_ports:
            ports_str = ", ".join(
                f"{p} ({PORT_NAMES.get(p, 'unknown')})" for p in open_ports
            )
            table.add_row("Open Ports", ports_str)
        else:
            table.add_row("Open Ports", "[green]None[/green]")

        critical = ports_result["critical_ports"]
        if critical:
            crit_str = ", ".join(
                f"[red]{p} ({PORT_NAMES.get(p, 'unknown')})[/red]" for p in critical
            )
            table.add_row("Critical Ports", crit_str)
        else:
            table.add_row("Critical Ports", "[green]None[/green]")

    console.print(table)
    console.print()
    return ports_result["status"]


def display_sca_results(sca_result: dict[str, Any]) -> str:
    console.print("[bold white]SCA — Analyse des dépendances[/bold white]")

    table = Table(box=box.ROUNDED, show_header=True, header_style="bold magenta")
    table.add_column("Property", style="dim", width=22)
    table.add_column("Value")

    if sca_result.get("error"):
        table.add_row("Status", colorize_status("CRITICAL"))
        table.add_row("Error", f"[red]{sca_result['error']}[/red]")
    else:
        status = sca_result["status"]
        table.add_row("Status", colorize_status(status))
        table.add_row("Packages scanned", str(sca_result["total_packages"]))
        total = sca_result["total_vulns"]
        total_color = "green" if total == 0 else ("yellow" if status == "WARNING" else "red")
        table.add_row("Vulnerabilities", f"[{total_color}]{total}[/{total_color}]")

        for vuln in sca_result["vulns"]:
            sev = vuln["severity"]
            sev_color = {"CRITICAL": "red", "HIGH": "red", "MEDIUM": "yellow", "LOW": "blue"}.get(sev, "white")
            cve_str = ", ".join(vuln["cve_ids"])
            table.add_row(
                f"[{sev_color}]{vuln['package']} ({vuln['version']})[/{sev_color}]",
                f"[{sev_color}][{sev}][/{sev_color}] {cve_str}\n[dim]{vuln['summary']}[/dim]",
            )

    console.print(table)
    console.print()
    return sca_result["status"]


def display_secrets_results(secrets_result: dict[str, Any]) -> str:
    console.print("[bold white]Secrets Detection[/bold white]")

    table = Table(box=box.ROUNDED, show_header=True, header_style="bold magenta")
    table.add_column("Property", style="dim", width=22)
    table.add_column("Value")

    if secrets_result.get("error"):
        table.add_row("Status", colorize_status("CRITICAL"))
        table.add_row("Error", f"[red]{secrets_result['error']}[/red]")
    else:
        status = secrets_result["status"]
        table.add_row("Status", colorize_status(status))
        table.add_row("Files scanned", str(secrets_result["total_files"]))
        total = secrets_result["total_findings"]
        total_color = "green" if total == 0 else ("yellow" if status == "WARNING" else "red")
        table.add_row("Secrets found", f"[{total_color}]{total}[/{total_color}]")

        for finding in secrets_result["findings"]:
            table.add_row(
                f"[red]{finding['pattern']}[/red]",
                f"[dim]{finding['file']}[/dim] line {finding['line']} — [yellow]{finding['preview']}[/yellow]",
            )

    console.print(table)
    console.print()
    return secrets_result["status"]


def display_email_results(email_result: dict[str, Any]) -> str:
    console.print("[bold white]Email Security (SPF / DKIM / DMARC)[/bold white]")
    table = Table(box=box.ROUNDED, show_header=True, header_style="bold magenta")
    table.add_column("Check", style="dim", width=22)
    table.add_column("Value")

    if email_result.get("error"):
        table.add_row("Status", colorize_status("CRITICAL"))
        table.add_row("Error", f"[red]{email_result['error']}[/red]")
    else:
        table.add_row("Status", colorize_status(email_result["status"]))
        spf = email_result["spf"]
        table.add_row("SPF", "[green]Présent[/green]" if spf.get("found") else "[red]Absent[/red]")
        if spf.get("found") and not spf.get("strict"):
            table.add_row("SPF strictness", "[yellow]Non strict (~all)[/yellow]")
        dkim = email_result["dkim"]
        table.add_row("DKIM", f"[green]Présent (selector: {dkim['selector']})[/green]" if dkim.get("found") else "[red]Absent[/red]")
        dmarc = email_result["dmarc"]
        if dmarc.get("found"):
            policy_color = "green" if dmarc["policy"] in ("reject", "quarantine") else "yellow"
            table.add_row("DMARC", f"[{policy_color}]Présent (p={dmarc['policy']})[/{policy_color}]")
        else:
            table.add_row("DMARC", "[red]Absent[/red]")
        for issue in email_result["issues"]:
            table.add_row("[yellow]Issue[/yellow]", issue)

    console.print(table)
    console.print()
    return email_result["status"]


def display_cookie_results(cookie_result: dict[str, Any]) -> str:
    console.print("[bold white]Cookie Security[/bold white]")
    table = Table(box=box.ROUNDED, show_header=True, header_style="bold magenta")
    table.add_column("Property", style="dim", width=22)
    table.add_column("Value")

    if cookie_result.get("error"):
        table.add_row("Status", colorize_status("CRITICAL"))
        table.add_row("Error", f"[red]{cookie_result['error']}[/red]")
    else:
        table.add_row("Status", colorize_status(cookie_result["status"]))
        table.add_row("Cookies found", str(cookie_result["total_cookies"]))
        issues_count = cookie_result["total_issues"]
        ic = "green" if issues_count == 0 else ("yellow" if cookie_result["status"] == "WARNING" else "red")
        table.add_row("Issues", f"[{ic}]{issues_count}[/{ic}]")
        for issue in cookie_result["issues"]:
            table.add_row(f"[yellow]{issue['cookie']}[/yellow]", issue["issue"])

    console.print(table)
    console.print()
    return cookie_result["status"]


def display_cors_results(cors_result: dict[str, Any]) -> str:
    console.print("[bold white]CORS Audit[/bold white]")
    table = Table(box=box.ROUNDED, show_header=True, header_style="bold magenta")
    table.add_column("Property", style="dim", width=22)
    table.add_column("Value")

    if cors_result.get("error"):
        table.add_row("Status", colorize_status("CRITICAL"))
        table.add_row("Error", f"[red]{cors_result['error']}[/red]")
    else:
        table.add_row("Status", colorize_status(cors_result["status"]))
        acao = cors_result["allow_origin"] or "[dim]non défini[/dim]"
        table.add_row("Allow-Origin", acao)
        acac = cors_result["allow_credentials"] or "[dim]non défini[/dim]"
        table.add_row("Allow-Credentials", acac)
        table.add_row("Vulnerable", "[red]Oui[/red]" if cors_result["vulnerable"] else "[green]Non[/green]")
        for issue in cors_result["issues"]:
            table.add_row("[yellow]Issue[/yellow]", issue)

    console.print(table)
    console.print()
    return cors_result["status"]


def display_ip_reputation_results(ip_result: dict[str, Any]) -> str:
    console.print("[bold white]IP Reputation (DNSBL)[/bold white]")
    table = Table(box=box.ROUNDED, show_header=True, header_style="bold magenta")
    table.add_column("Property", style="dim", width=22)
    table.add_column("Value")

    if ip_result.get("error") and not ip_result.get("ip"):
        table.add_row("Status", colorize_status("CRITICAL"))
        table.add_row("Error", f"[red]{ip_result['error']}[/red]")
    else:
        table.add_row("Status", colorize_status(ip_result["status"]))
        table.add_row("IP", str(ip_result.get("ip", "—")))
        if ip_result.get("error"):
            table.add_row("Info", f"[dim]{ip_result['error']}[/dim]")
        listed = ip_result.get("listed_in", [])
        if listed:
            for entry in listed:
                table.add_row(f"[red]Listed in[/red]", f"{entry['label']} ({entry['category']})")
        else:
            table.add_row("Blacklists", "[green]Aucune[/green]")

    console.print(table)
    console.print()
    return ip_result["status"]


def display_dns_results(dns_result: dict[str, Any]) -> str:
    console.print("[bold white]DNS & Subdomains[/bold white]")
    table = Table(box=box.ROUNDED, show_header=True, header_style="bold magenta")
    table.add_column("Property", style="dim", width=22)
    table.add_column("Value")
    if dns_result.get("error"):
        table.add_row("Status", colorize_status("CRITICAL"))
        table.add_row("Error", f"[red]{dns_result['error']}[/red]")
    else:
        table.add_row("Status", colorize_status(dns_result["status"]))
        table.add_row("Subdomains found", str(dns_result["total_found"]))
        zt = dns_result.get("zone_transfer", {})
        table.add_row("Zone Transfer", "[red]VULNERABLE[/red]" if zt.get("vulnerable") else "[green]Refusé[/green]")
        for s in dns_result["found"]:
            table.add_row(f"[cyan]{s['subdomain']}[/cyan]", s["ip"])
    console.print(table)
    console.print()
    return dns_result["status"]


def display_cms_results(cms_result: dict[str, Any]) -> str:
    console.print("[bold white]CMS Detection[/bold white]")
    table = Table(box=box.ROUNDED, show_header=True, header_style="bold magenta")
    table.add_column("Property", style="dim", width=22)
    table.add_column("Value")
    if cms_result.get("error"):
        table.add_row("Status", colorize_status("CRITICAL"))
        table.add_row("Error", f"[red]{cms_result['error']}[/red]")
    else:
        table.add_row("Status", colorize_status(cms_result["status"]))
        cms = cms_result["cms"]
        table.add_row("CMS", f"[yellow]{cms}[/yellow]" if cms != "Unknown" else "[green]Unknown[/green]")
        if cms_result["version"]:
            table.add_row("Version", f"[red]{cms_result['version']}[/red]")
        table.add_row("Confidence", str(cms_result["confidence"]))
    console.print(table)
    console.print()
    return cms_result["status"]


def display_breach_results(breach_result: dict[str, Any]) -> str:
    console.print("[bold white]Data Breach (HIBP)[/bold white]")
    table = Table(box=box.ROUNDED, show_header=True, header_style="bold magenta")
    table.add_column("Property", style="dim", width=22)
    table.add_column("Value")
    if breach_result.get("error") and breach_result["status"] != "OK":
        table.add_row("Status", colorize_status(breach_result["status"]))
        table.add_row("Info", f"[dim]{breach_result['error']}[/dim]")
    else:
        table.add_row("Status", colorize_status(breach_result["status"]))
        total = breach_result["total"]
        tc = "green" if total == 0 else ("yellow" if breach_result["status"] == "WARNING" else "red")
        table.add_row("Breaches found", f"[{tc}]{total}[/{tc}]")
        for b in breach_result.get("breaches", []):
            table.add_row(f"[red]{b['name']}[/red]", f"{b.get('breach_date','')} — {b.get('pwn_count',0):,} comptes")
        for a in breach_result.get("accounts", []):
            table.add_row(f"[red]{a['email']}[/red]", ", ".join(a.get("breaches", [])))
    console.print(table)
    console.print()
    return breach_result["status"]


def display_waf_results(waf_result: dict[str, Any]) -> str:
    console.print("[bold white]WAF Detection[/bold white]")
    table = Table(box=box.ROUNDED, show_header=True, header_style="bold magenta")
    table.add_column("Property", style="dim", width=22)
    table.add_column("Value")
    if waf_result.get("error"):
        table.add_row("Status", colorize_status("WARNING"))
        table.add_row("Error", f"[dim]{waf_result['error']}[/dim]")
    else:
        table.add_row("Status", colorize_status(waf_result["status"]))
        detected = waf_result["detected"]
        table.add_row("WAF détecté", f"[green]Oui — {waf_result['waf_name']}[/green]" if detected else "[yellow]Non détecté[/yellow]")
        if waf_result.get("method"):
            table.add_row("Méthode", waf_result["method"])
    console.print(table)
    console.print()
    return waf_result["status"]


def display_tech_results(tech_result: dict[str, Any]) -> str:
    console.print("[bold white]Technology Fingerprint[/bold white]")
    table = Table(box=box.ROUNDED, show_header=True, header_style="bold magenta")
    table.add_column("Category", style="dim", width=22)
    table.add_column("Technologies")
    if tech_result.get("error") and tech_result["status"] == "CRITICAL":
        table.add_row("Status", colorize_status("CRITICAL"))
        table.add_row("Error", f"[red]{tech_result['error']}[/red]")
    else:
        table.add_row("Status", colorize_status(tech_result["status"]))
        table.add_row("Total detected", str(tech_result["total"]))
        for cat, names in tech_result["technologies"].items():
            table.add_row(f"[cyan]{cat}[/cyan]", ", ".join(names))
        if tech_result.get("error"):
            table.add_row("[yellow]Warning[/yellow]", tech_result["error"])
    console.print(table)
    console.print()
    return tech_result["status"]


def display_tls_results(tls_result: dict[str, Any]) -> str:
    console.print("[bold white]TLS Deep Audit[/bold white]")
    table = Table(box=box.ROUNDED, show_header=True, header_style="bold magenta")
    table.add_column("Property", style="dim", width=22)
    table.add_column("Value")
    if tls_result.get("error") and tls_result["status"] == "CRITICAL" and not tls_result["supported_protocols"]:
        table.add_row("Status", colorize_status("CRITICAL"))
        table.add_row("Error", f"[red]{tls_result['error']}[/red]")
    else:
        table.add_row("Status", colorize_status(tls_result["status"]))
        protos = ", ".join(tls_result["supported_protocols"]) or "[dim]none[/dim]"
        table.add_row("Protocols", protos)
        weak_p = tls_result["weak_protocols"]
        if weak_p:
            table.add_row("Weak protocols", f"[red]{', '.join(weak_p)}[/red]")
        hsts = tls_result["hsts"]
        if hsts.get("present"):
            preload = "[green]Yes[/green]" if hsts["preload"] else "[yellow]No[/yellow]"
            table.add_row("HSTS", f"max-age={hsts['max_age']} | preload={preload}")
        else:
            table.add_row("HSTS", "[red]Absent[/red]")
        weak_c = tls_result["weak_ciphers"]
        if weak_c:
            table.add_row("Weak ciphers", f"[red]{', '.join(weak_c)}[/red]")
        else:
            table.add_row("Weak ciphers", "[green]None[/green]")
        cert = tls_result.get("certificate")
        if cert:
            table.add_row("Cert subject", cert.get("subject", ""))
            table.add_row("Cert issuer",  cert.get("issuer", ""))
    console.print(table)
    console.print()
    return tls_result["status"]


def display_takeover_results(takeover_result: dict[str, Any]) -> str:
    console.print("[bold white]Subdomain Takeover[/bold white]")
    table = Table(box=box.ROUNDED, show_header=True, header_style="bold magenta")
    table.add_column("Property", style="dim", width=22)
    table.add_column("Value")
    table.add_row("Status", colorize_status(takeover_result["status"]))
    table.add_row("Checked", str(takeover_result["total_checked"]))
    vuln_count = takeover_result["total_vulnerable"]
    vc = "green" if vuln_count == 0 else "red"
    table.add_row("Vulnerable", f"[{vc}]{vuln_count}[/{vc}]")
    for v in takeover_result["vulnerable"]:
        table.add_row(f"[red]{v['subdomain']}[/red]", f"{v['service']} — {v['reason']}")
    if takeover_result.get("error"):
        table.add_row("[yellow]Info[/yellow]", takeover_result["error"])
    console.print(table)
    console.print()
    return takeover_result["status"]


def display_threat_intel_results(ti_result: dict[str, Any]) -> str:
    console.print("[bold white]Threat Intelligence (Shodan)[/bold white]")
    table = Table(box=box.ROUNDED, show_header=True, header_style="bold magenta")
    table.add_column("Property", style="dim", width=22)
    table.add_column("Value")
    if ti_result.get("error") and not ti_result.get("ip"):
        table.add_row("Status", colorize_status("CRITICAL"))
        table.add_row("Error", f"[red]{ti_result['error']}[/red]")
    else:
        table.add_row("Status", colorize_status(ti_result["status"]))
        table.add_row("IP", str(ti_result.get("ip", "—")))
        ports = ti_result["open_ports"]
        table.add_row("Open ports", ", ".join(str(p) for p in ports) if ports else "[green]—[/green]")
        cves = ti_result["cves"]
        if cves:
            table.add_row("CVEs", f"[red]{', '.join(cves[:5])}{'…' if len(cves) > 5 else ''}[/red]")
        else:
            table.add_row("CVEs", "[green]None[/green]")
        tags = ti_result["tags"]
        if tags:
            table.add_row("Tags", ", ".join(tags))
        if ti_result.get("abuse_score") is not None:
            score = ti_result["abuse_score"]
            sc = "green" if score < 25 else ("yellow" if score < 75 else "red")
            table.add_row("Abuse score", f"[{sc}]{score}/100[/{sc}]")
        if ti_result.get("error"):
            table.add_row("[yellow]Warning[/yellow]", ti_result["error"])
    console.print(table)
    console.print()
    return ti_result["status"]


def display_http_methods_results(methods_result: dict[str, Any]) -> str:
    console.print("[bold white]HTTP Methods[/bold white]")
    table = Table(box=box.ROUNDED, show_header=True, header_style="bold magenta")
    table.add_column("Property", style="dim", width=22)
    table.add_column("Value")
    table.add_row("Status", colorize_status(methods_result["status"]))
    declared = methods_result["options_declared"]
    table.add_row("OPTIONS declares", ", ".join(declared) if declared else "[dim]—[/dim]")
    dangerous = methods_result["dangerous_allowed"]
    if dangerous:
        table.add_row("Dangerous methods", f"[red]{', '.join(dangerous)}[/red]")
    else:
        table.add_row("Dangerous methods", "[green]None[/green]")
    allowed = methods_result["allowed_methods"]
    if allowed:
        table.add_row("Allowed methods", ", ".join(allowed))
    console.print(table)
    console.print()
    return methods_result["status"]


def display_open_redirect_results(r: dict[str, Any]) -> str:
    console.print("[bold white]Open Redirect[/bold white]")
    table = Table(box=box.ROUNDED, show_header=True, header_style="bold magenta")
    table.add_column("Property", style="dim", width=22)
    table.add_column("Value")
    table.add_row("Status", colorize_status(r["status"]))
    table.add_row("Probes sent", str(r["tested"]))
    vuln_c = "green" if not r["vulnerable"] else "red"
    table.add_row("Vulnerable", f"[{vuln_c}]{'Oui' if r['vulnerable'] else 'Non'}[/{vuln_c}]")
    for f in r["findings"]:
        table.add_row(f"[red]{f['param']}[/red]", f"payload: {f['payload']} → {f['location']}")
    console.print(table)
    console.print()
    return r["status"]


def display_clickjacking_results(r: dict[str, Any]) -> str:
    console.print("[bold white]Clickjacking[/bold white]")
    table = Table(box=box.ROUNDED, show_header=True, header_style="bold magenta")
    table.add_column("Property", style="dim", width=22)
    table.add_column("Value")
    if r.get("error") and not r.get("xfo"):
        table.add_row("Status", colorize_status("CRITICAL"))
        table.add_row("Error", f"[red]{r['error']}[/red]")
    else:
        table.add_row("Status", colorize_status(r["status"]))
        xfo = r["xfo"]
        table.add_row("X-Frame-Options", f"[green]{xfo['value']}[/green]" if xfo.get("protected") else f"[red]{xfo.get('value') or 'Absent'}[/red]")
        csp = r["csp_frame_ancestors"]
        table.add_row("CSP frame-ancestors", f"[green]{csp['value']}[/green]" if csp.get("protected") else f"[red]{csp.get('value') or 'Absent'}[/red]")
        table.add_row("Vulnerable", "[red]Oui[/red]" if r["vulnerable"] else "[green]Non[/green]")
    console.print(table)
    console.print()
    return r["status"]


def display_directory_listing_results(r: dict[str, Any]) -> str:
    console.print("[bold white]Directory Listing & Sensitive Paths[/bold white]")
    table = Table(box=box.ROUNDED, show_header=True, header_style="bold magenta")
    table.add_column("Property", style="dim", width=22)
    table.add_column("Value")
    table.add_row("Status", colorize_status(r["status"]))
    table.add_row("Critical findings", f"[{'red' if r['total_critical'] else 'green'}]{r['total_critical']}[/{'red' if r['total_critical'] else 'green'}]")
    table.add_row("Warning findings",  f"[{'yellow' if r['total_warning'] else 'green'}]{r['total_warning']}[/{'yellow' if r['total_warning'] else 'green'}]")
    for f in r["findings"]:
        sev_c = "red" if f["severity"] == "CRITICAL" else "yellow"
        table.add_row(f"[{sev_c}]{f['path']}[/{sev_c}]", f"{f['category']} — HTTP {f['status_code']}")
    console.print(table)
    console.print()
    return r["status"]


def display_robots_results(r: dict[str, Any]) -> str:
    console.print("[bold white]Robots.txt & Sitemap[/bold white]")
    table = Table(box=box.ROUNDED, show_header=True, header_style="bold magenta")
    table.add_column("Property", style="dim", width=22)
    table.add_column("Value")
    table.add_row("Status", colorize_status(r["status"]))
    table.add_row("robots.txt", "[green]Trouvé[/green]" if r["robots_found"] else "[dim]Absent[/dim]")
    table.add_row("Disallow entries", str(len(r["disallowed_paths"])))
    sensitive = r["sensitive_disallowed"]
    if sensitive:
        table.add_row("[yellow]Chemins sensibles[/yellow]", "\n".join(sensitive[:5]))
    table.add_row("Sitemap", "[green]Trouvé[/green]" if r["sitemap_found"] else "[dim]Absent[/dim]")
    if r["sitemap_found"]:
        table.add_row("URLs sitemap", str(r["sitemap_url_count"]))
    console.print(table)
    console.print()
    return r["status"]


def display_jwt_results(r: dict[str, Any]) -> str:
    console.print("[bold white]JWT Security[/bold white]")
    table = Table(box=box.ROUNDED, show_header=True, header_style="bold magenta")
    table.add_column("Property", style="dim", width=22)
    table.add_column("Value")
    if r.get("error") and r["status"] == "CRITICAL" and r["tokens_found"] == 0:
        table.add_row("Status", colorize_status("CRITICAL"))
        table.add_row("Error", f"[red]{r['error']}[/red]")
    else:
        table.add_row("Status", colorize_status(r["status"]))
        table.add_row("Tokens détectés", str(r["tokens_found"]))
        for a in r["analyses"]:
            sev_c = "red" if a["severity"] == "CRITICAL" else ("yellow" if a["severity"] == "WARNING" else "green")
            issues_str = ", ".join(a["issues"]) if a["issues"] else "OK"
            table.add_row(f"[{sev_c}]{a['token'][:40]}…[/{sev_c}]", issues_str)
    console.print(table)
    console.print()
    return r["status"]


def display_summary(url: str, statuses: list[str]) -> None:
    overall = get_overall_status(statuses)
    color = STATUS_COLORS.get(overall, "white")

    summary_lines = [
        f"[bold]Target:[/bold] {url}",
        "",
        f"[bold]Overall Risk:[/bold] [{color}]{overall}[/{color}]",
    ]

    if overall == "OK":
        summary_lines.append("[green]No critical issues detected.[/green]")
    elif overall == "WARNING":
        summary_lines.append("[yellow]Some issues require attention.[/yellow]")
    else:
        summary_lines.append("[red]Critical vulnerabilities detected. Immediate action recommended.[/red]")

    console.print(
        Panel(
            "\n".join(summary_lines),
            title="[bold]Scan Summary[/bold]",
            border_style=color,
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Cyber-Scanner: External attack surface scanner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Example:\n  python main.py --url https://example.com\n  python main.py --url https://example.com --skip-ports",
    )
    parser.add_argument(
        "--url",
        required=True,
        help="Target URL to scan (e.g. https://example.com)",
    )
    parser.add_argument(
        "--skip-ports",
        action="store_true",
        help="Skip the nmap port scan",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Générer un rapport PDF dans reports/rapport_audit.pdf",
    )
    parser.add_argument(
        "--requirements",
        metavar="PATH",
        help="Path to requirements.txt to scan for CVEs (SCA)",
    )
    parser.add_argument(
        "--package-json",
        metavar="PATH",
        help="Path to package.json to scan for CVEs (SCA)",
    )
    parser.add_argument(
        "--secrets",
        metavar="PATH",
        help="Directory or file to scan for leaked secrets",
    )
    parser.add_argument(
        "--remediate",
        action="store_true",
        help="Generate remediation scripts in remediation/",
    )
    parser.add_argument("--skip-email",   action="store_true", help="Skip email security check (SPF/DKIM/DMARC)")
    parser.add_argument("--skip-cookies", action="store_true", help="Skip cookie security check")
    parser.add_argument("--skip-cors",    action="store_true", help="Skip CORS audit")
    parser.add_argument("--skip-ip-rep",  action="store_true", help="Skip IP reputation check")
    parser.add_argument("--skip-dns",     action="store_true", help="Skip DNS/subdomain scan")
    parser.add_argument("--skip-cms",     action="store_true", help="Skip CMS detection")
    parser.add_argument("--skip-waf",     action="store_true", help="Skip WAF detection")
    parser.add_argument("--hibp-key",       metavar="KEY",    help="HaveIBeenPwned API key for breach check")
    parser.add_argument("--breach-email",   metavar="EMAIL",  help="Email to check for data breaches")
    parser.add_argument("--breach-domain",  metavar="DOMAIN", help="Domain to check for data breaches")
    parser.add_argument("--skip-tech",      action="store_true", help="Skip technology fingerprinting")
    parser.add_argument("--skip-tls",       action="store_true", help="Skip deep TLS audit")
    parser.add_argument("--skip-takeover",  action="store_true", help="Skip subdomain takeover check")
    parser.add_argument("--skip-threat",    action="store_true", help="Skip threat intelligence (Shodan)")
    parser.add_argument("--skip-methods",   action="store_true", help="Skip HTTP methods check")
    parser.add_argument("--abuseipdb-key",    metavar="KEY",  help="AbuseIPDB API key (optional, for threat intel)")
    parser.add_argument("--skip-redirects",   action="store_true", help="Skip open redirect check")
    parser.add_argument("--skip-clickjacking",action="store_true", help="Skip clickjacking check")
    parser.add_argument("--skip-dirlist",     action="store_true", help="Skip directory listing check")
    parser.add_argument("--skip-robots",      action="store_true", help="Skip robots.txt / sitemap analysis")
    parser.add_argument("--skip-jwt",         action="store_true", help="Skip JWT security check")
    args = parser.parse_args()

    url: str = args.url
    # Ensure URL has a scheme for requests
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    hostname: str = extract_hostname(url)

    display_banner()
    console.print(f"[bold]Target:[/bold] [cyan]{url}[/cyan]")
    console.print(f"[bold]Hostname:[/bold] [cyan]{hostname}[/cyan]")
    console.print()

    statuses: list[str] = []

    # --- SSL Check ---
    console.print("[dim]Running SSL/TLS check...[/dim]")
    ssl_result = check_ssl(hostname)
    ssl_status = display_ssl_results(ssl_result, hostname)
    statuses.append(ssl_status)

    # --- Headers Check ---
    console.print("[dim]Running HTTP headers check...[/dim]")
    headers_result = check_headers(url)
    headers_status = display_headers_results(headers_result)
    statuses.append(headers_status)

    # --- Port Scan ---
    ports_result: dict[str, Any] = {}
    ports_skipped: bool = args.skip_ports
    if args.skip_ports:
        console.print("[dim]Port scan skipped (--skip-ports).[/dim]\n")
    else:
        console.print("[dim]Running port scan (this may take a moment)...[/dim]")
        ports_result = scan_ports(hostname)
        ports_status = display_ports_results(ports_result)
        statuses.append(ports_status)

    # --- SCA Check ---
    sca_result: dict[str, Any] = {}
    sca_run: bool = bool(args.requirements or args.package_json)
    if sca_run:
        console.print("[dim]Running SCA dependency scan via OSV.dev...[/dim]")
        sca_result = check_sca(
            requirements_path=args.requirements,
            package_json_path=args.package_json,
        )
        sca_status = display_sca_results(sca_result)
        statuses.append(sca_status)
    else:
        console.print("[dim]SCA skipped (use --requirements / --package-json to enable).[/dim]\n")

    # --- Email Security ---
    email_result: dict[str, Any] = {}
    if args.skip_email:
        console.print("[dim]Email security skipped (--skip-email).[/dim]\n")
    else:
        console.print("[dim]Running email security check (SPF/DKIM/DMARC)...[/dim]")
        email_result = check_email_security(hostname)
        statuses.append(display_email_results(email_result))

    # --- Cookie Security ---
    cookie_result: dict[str, Any] = {}
    if args.skip_cookies:
        console.print("[dim]Cookie security skipped (--skip-cookies).[/dim]\n")
    else:
        console.print("[dim]Running cookie security check...[/dim]")
        cookie_result = check_cookies(url)
        statuses.append(display_cookie_results(cookie_result))

    # --- CORS Audit ---
    cors_result: dict[str, Any] = {}
    if args.skip_cors:
        console.print("[dim]CORS audit skipped (--skip-cors).[/dim]\n")
    else:
        console.print("[dim]Running CORS audit...[/dim]")
        cors_result = check_cors(url)
        statuses.append(display_cors_results(cors_result))

    # --- IP Reputation ---
    ip_result: dict[str, Any] = {}
    if args.skip_ip_rep:
        console.print("[dim]IP reputation skipped (--skip-ip-rep).[/dim]\n")
    else:
        console.print("[dim]Running IP reputation check...[/dim]")
        ip_result = check_ip_reputation(hostname)
        statuses.append(display_ip_reputation_results(ip_result))

    # --- DNS / Subdomains ---
    dns_result: dict[str, Any] = {}
    if args.skip_dns:
        console.print("[dim]DNS scan skipped (--skip-dns).[/dim]\n")
    else:
        console.print("[dim]Running DNS & subdomain scan...[/dim]")
        dns_result = scan_subdomains(hostname)
        statuses.append(display_dns_results(dns_result))

    # --- CMS Detection ---
    cms_result: dict[str, Any] = {}
    if args.skip_cms:
        console.print("[dim]CMS detection skipped (--skip-cms).[/dim]\n")
    else:
        console.print("[dim]Running CMS detection...[/dim]")
        cms_result = detect_cms(url)
        statuses.append(display_cms_results(cms_result))

    # --- WAF Detection ---
    waf_result: dict[str, Any] = {}
    if args.skip_waf:
        console.print("[dim]WAF detection skipped (--skip-waf).[/dim]\n")
    else:
        console.print("[dim]Running WAF detection...[/dim]")
        waf_result = detect_waf(url)
        statuses.append(display_waf_results(waf_result))

    # --- Data Breach ---
    breach_result: dict[str, Any] = {}
    breach_target = args.breach_email or args.breach_domain
    breach_mode = "email" if args.breach_email else "domain"
    if breach_target:
        console.print("[dim]Running data breach check (HIBP)...[/dim]")
        breach_result = check_breach(breach_target, api_key=args.hibp_key, mode=breach_mode)
        statuses.append(display_breach_results(breach_result))
    else:
        console.print("[dim]Breach check skipped (use --breach-email or --breach-domain).[/dim]\n")

    # --- Tech Fingerprint ---
    tech_result: dict[str, Any] = {}
    if args.skip_tech:
        console.print("[dim]Tech fingerprint skipped (--skip-tech).[/dim]\n")
    else:
        console.print("[dim]Running technology fingerprinting...[/dim]")
        tech_result = fingerprint_tech(url)
        statuses.append(display_tech_results(tech_result))

    # --- TLS Deep Audit ---
    tls_result: dict[str, Any] = {}
    if args.skip_tls:
        console.print("[dim]TLS audit skipped (--skip-tls).[/dim]\n")
    else:
        console.print("[dim]Running deep TLS audit...[/dim]")
        tls_result = audit_tls(hostname)
        statuses.append(display_tls_results(tls_result))

    # --- Subdomain Takeover ---
    takeover_result: dict[str, Any] = {}
    takeover_skipped: bool = args.skip_takeover
    if args.skip_takeover:
        console.print("[dim]Subdomain takeover skipped (--skip-takeover).[/dim]\n")
    else:
        console.print("[dim]Running subdomain takeover check...[/dim]")
        found_subs = [s["subdomain"] for s in dns_result.get("found", [])] if dns_result else []
        takeover_result = check_subdomain_takeover(found_subs)
        statuses.append(display_takeover_results(takeover_result))

    # --- Threat Intelligence ---
    ti_result: dict[str, Any] = {}
    if args.skip_threat:
        console.print("[dim]Threat intelligence skipped (--skip-threat).[/dim]\n")
    else:
        console.print("[dim]Running threat intelligence (Shodan InternetDB)...[/dim]")
        ti_result = get_threat_intel(hostname, abuseipdb_key=getattr(args, "abuseipdb_key", None))
        statuses.append(display_threat_intel_results(ti_result))

    # --- HTTP Methods ---
    methods_result: dict[str, Any] = {}
    if args.skip_methods:
        console.print("[dim]HTTP methods check skipped (--skip-methods).[/dim]\n")
    else:
        console.print("[dim]Running HTTP methods check...[/dim]")
        methods_result = check_http_methods(url)
        statuses.append(display_http_methods_results(methods_result))

    # --- Open Redirect ---
    redirect_result: dict[str, Any] = {}
    if args.skip_redirects:
        console.print("[dim]Open redirect skipped (--skip-redirects).[/dim]\n")
    else:
        console.print("[dim]Running open redirect check...[/dim]")
        redirect_result = check_open_redirect(url)
        statuses.append(display_open_redirect_results(redirect_result))

    # --- Clickjacking ---
    clickjacking_result: dict[str, Any] = {}
    if args.skip_clickjacking:
        console.print("[dim]Clickjacking check skipped (--skip-clickjacking).[/dim]\n")
    else:
        console.print("[dim]Running clickjacking check...[/dim]")
        clickjacking_result = check_clickjacking(url)
        statuses.append(display_clickjacking_results(clickjacking_result))

    # --- Directory Listing ---
    dirlist_result: dict[str, Any] = {}
    if args.skip_dirlist:
        console.print("[dim]Directory listing skipped (--skip-dirlist).[/dim]\n")
    else:
        console.print("[dim]Running directory listing & sensitive path check...[/dim]")
        dirlist_result = check_directory_listing(url)
        statuses.append(display_directory_listing_results(dirlist_result))

    # --- Robots / Sitemap ---
    robots_result: dict[str, Any] = {}
    if args.skip_robots:
        console.print("[dim]Robots/sitemap skipped (--skip-robots).[/dim]\n")
    else:
        console.print("[dim]Running robots.txt & sitemap analysis...[/dim]")
        robots_result = analyse_robots_sitemap(url)
        statuses.append(display_robots_results(robots_result))

    # --- JWT ---
    jwt_result: dict[str, Any] = {}
    if args.skip_jwt:
        console.print("[dim]JWT check skipped (--skip-jwt).[/dim]\n")
    else:
        console.print("[dim]Running JWT security check...[/dim]")
        jwt_result = check_jwt(url)
        statuses.append(display_jwt_results(jwt_result))

    # --- Secrets Detection ---
    secrets_result: dict[str, Any] = {}
    if args.secrets:
        console.print("[dim]Running secrets detection...[/dim]")
        secrets_result = check_secrets(args.secrets)
        secrets_status = display_secrets_results(secrets_result)
        statuses.append(secrets_status)
    else:
        console.print("[dim]Secrets scan skipped (use --secrets PATH to enable).[/dim]\n")

    # --- Summary ---
    display_summary(url, statuses)

    # --- PDF Report ---
    if args.report:
        console.print()
        console.print("[dim]Génération du rapport PDF...[/dim]")
        report_path = generate_report(
            target_url=url,
            ssl_result=ssl_result,
            headers_result=headers_result,
            port_result=ports_result,
            ports_skipped=ports_skipped,
            sca_result=sca_result,
            sca_skipped=not sca_run,
            email_result=email_result,
            email_skipped=args.skip_email,
            cookie_result=cookie_result,
            cookie_skipped=args.skip_cookies,
            cors_result=cors_result,
            cors_skipped=args.skip_cors,
            ip_result=ip_result,
            ip_skipped=args.skip_ip_rep,
            dns_result=dns_result,
            dns_skipped=args.skip_dns,
            cms_result=cms_result,
            cms_skipped=args.skip_cms,
            waf_result=waf_result,
            waf_skipped=args.skip_waf,
            breach_result=breach_result,
            breach_skipped=not bool(breach_target),
            tech_result=tech_result,
            tech_skipped=args.skip_tech,
            tls_result=tls_result,
            tls_skipped=args.skip_tls,
            takeover_result=takeover_result,
            takeover_skipped=takeover_skipped,
            ti_result=ti_result,
            ti_skipped=args.skip_threat,
            methods_result=methods_result,
            methods_skipped=args.skip_methods,
            redirect_result=redirect_result,
            redirect_skipped=args.skip_redirects,
            clickjacking_result=clickjacking_result,
            clickjacking_skipped=args.skip_clickjacking,
            dirlist_result=dirlist_result,
            dirlist_skipped=args.skip_dirlist,
            robots_result=robots_result,
            robots_skipped=args.skip_robots,
            jwt_result=jwt_result,
            jwt_skipped=args.skip_jwt,
        )
        console.print(
            Panel.fit(
                f"[bold green]Rapport PDF généré :[/bold green] [cyan]{report_path}[/cyan]",
                border_style="green",
            )
        )

    # --- Remediation Scripts ---
    if args.remediate:
        console.print()
        console.print("[dim]Génération des scripts de remédiation...[/dim]")
        generated = generate_remediation(
            target_url=url,
            port_result=ports_result or None,
            headers_result=headers_result or None,
            sca_result=sca_result or None,
        )
        lines = [f"[bold green]Scripts de remédiation générés dans[/bold green] [cyan]remediation/[/cyan]"]
        script_labels = {
            "ufw":     "ufw_setup.sh            — règles pare-feu UFW",
            "ssh":     "ssh_hardening.sh        — durcissement SSH",
            "fastapi": "fastapi_security_middleware.py — headers de sécurité",
            "upgrade": "upgrade_deps.sh         — mise à jour dépendances vulnérables",
        }
        for key, label in script_labels.items():
            if key in generated:
                lines.append(f"  [green]+[/green] {label}")
        console.print(Panel("\n".join(lines), border_style="green"))


if __name__ == "__main__":
    main()
