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
