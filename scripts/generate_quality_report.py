"""
Rapport qualité PDF — Cyber-Vault

Collecte et consolide les métriques de qualité du projet :
  - Couverture de tests (pytest --cov)
  - Complexité cyclomatique (radon)
  - Audit de sécurité (bandit + npm audit)
  - Statistiques Git
  - Statistiques de code (fichiers / lignes)

Usage:
    python scripts/generate_quality_report.py [output.pdf]

Sortie par défaut : reports/quality-report-YYYYMMDD.pdf
"""
from __future__ import annotations

import json
import platform
import subprocess
import sys

_WIN = platform.system() == "Windows"
_NPM = "npm.cmd" if _WIN else "npm"
from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# ── Palette ────────────────────────────────────────────────────────────────────
NAVY   = colors.HexColor("#0f172a")
CYAN   = colors.HexColor("#06b6d4")
GREEN  = colors.HexColor("#22c55e")
RED    = colors.HexColor("#ef4444")
YELLOW = colors.HexColor("#f59e0b")
GRAY   = colors.HexColor("#64748b")
LGRAY  = colors.HexColor("#f1f5f9")
WHITE  = colors.white

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"


# ── Collecte des métriques ──────────────────────────────────────────────────────

def _run(cmd: list[str], cwd: Path | None = None) -> tuple[int, str, str]:
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
    return result.returncode, result.stdout, result.stderr


def collect_coverage() -> dict:
    """Lance pytest avec --cov et parse le résumé."""
    print("  > Collecte de la couverture (pytest)...")
    _, stdout, _ = _run(
        ["python", "-m", "pytest", "--cov=app", "--cov-report=term-missing", "-q", "--no-header"],
        cwd=BACKEND,
    )
    data: dict = {"percent": 0, "covered": 0, "total": 0, "missing": 0, "files": []}
    for line in stdout.splitlines():
        if line.startswith("TOTAL"):
            parts = line.split()
            if len(parts) >= 4:
                data["total"] = int(parts[1])
                data["missing"] = int(parts[2])
                data["covered"] = data["total"] - data["missing"]
                pct = parts[3].replace("%", "")
                data["percent"] = int(pct) if pct.isdigit() else 0
        elif line and not line.startswith(("Name", "---", "TOTAL")) and "%" in line:
            parts = line.split()
            if len(parts) >= 4:
                data["files"].append({
                    "name": parts[0],
                    "stmts": parts[1],
                    "miss": parts[2],
                    "cover": parts[3],
                })
    return data


def collect_complexity() -> dict:
    """Analyse la complexité cyclomatique avec radon (si installé)."""
    print("  > Analyse de complexite (radon)...")
    rc, stdout, _ = _run(
        ["python", "-m", "radon", "cc", "app/", "-s", "-j"],
        cwd=BACKEND,
    )
    if rc != 0:
        return {"available": False}

    try:
        raw = json.loads(stdout)
    except json.JSONDecodeError:
        return {"available": False}

    all_functions = []
    for funcs in raw.values():
        for f in funcs:
            all_functions.append({
                "name": f.get("name", ""),
                "complexity": f.get("complexity", 0),
                "rank": f.get("rank", "A"),
            })

    total = len(all_functions)
    avg = sum(f["complexity"] for f in all_functions) / total if total else 0
    high = [f for f in all_functions if f["complexity"] > 10]
    top10 = sorted(all_functions, key=lambda x: x["complexity"], reverse=True)[:10]

    return {
        "available": True,
        "total_functions": total,
        "average": round(avg, 1),
        "high_complexity_count": len(high),
        "top10": top10,
    }


def collect_bandit() -> dict:
    """Audit sécurité Python avec bandit."""
    print("  > Audit securite Python (bandit)...")
    _, stdout, _ = _run(
        ["python", "-m", "bandit", "-r", "app/", "-f", "json", "-q"],
        cwd=BACKEND,
    )
    try:
        data = json.loads(stdout)
        metrics = data.get("metrics", {}).get("_totals", {})
        return {
            "available": True,
            "high": int(metrics.get("SEVERITY.HIGH", 0)),
            "medium": int(metrics.get("SEVERITY.MEDIUM", 0)),
            "low": int(metrics.get("SEVERITY.LOW", 0)),
        }
    except (json.JSONDecodeError, KeyError):
        return {"available": False}


def collect_npm_audit() -> dict:
    """Audit sécurité frontend avec npm audit."""
    print("  > Audit securite frontend (npm audit)...")
    _, stdout, _ = _run(
        [_NPM, "audit", "--json"],
        cwd=FRONTEND,
    )
    try:
        data = json.loads(stdout)
        vulns = data.get("metadata", {}).get("vulnerabilities", {})
        return {
            "available": True,
            "critical": vulns.get("critical", 0),
            "high": vulns.get("high", 0),
            "moderate": vulns.get("moderate", 0),
            "low": vulns.get("low", 0),
        }
    except (json.JSONDecodeError, KeyError):
        return {"available": False}


def collect_git_stats() -> dict:
    """Statistiques Git du projet."""
    print("  > Statistiques Git...")
    _, commits, _ = _run(["git", "rev-list", "--count", "HEAD"], cwd=ROOT)
    _, log, _ = _run(
        ["git", "log", "--format=%an", "--no-merges"],
        cwd=ROOT,
    )
    _, first_date, _ = _run(
        ["git", "log", "--reverse", "--format=%ai", "--max-count=1"],
        cwd=ROOT,
    )
    _, last_date, _ = _run(
        ["git", "log", "--format=%ai", "--max-count=1"],
        cwd=ROOT,
    )
    contributors = sorted(set(log.strip().splitlines()))
    return {
        "total_commits": commits.strip(),
        "contributors": contributors,
        "first_commit": first_date.strip()[:10] if first_date.strip() else "—",
        "last_commit": last_date.strip()[:10] if last_date.strip() else "—",
    }


def collect_code_stats() -> dict:
    """Compte les fichiers et lignes de code (Python + TypeScript)."""
    print("  > Statistiques de code...")
    py_files = list(BACKEND.rglob("*.py"))
    py_files = [f for f in py_files if "test" not in str(f) and "__pycache__" not in str(f) and "alembic" not in str(f)]
    ts_files = list((FRONTEND / "src").rglob("*.ts")) if (FRONTEND / "src").exists() else []
    ts_files = [f for f in ts_files if ".spec." not in f.name]

    def count_lines(files: list[Path]) -> int:
        total = 0
        for f in files:
            try:
                total += sum(1 for _ in f.open(encoding="utf-8", errors="ignore"))
            except OSError:
                pass
        return total

    return {
        "python_files": len(py_files),
        "python_lines": count_lines(py_files),
        "typescript_files": len(ts_files),
        "typescript_lines": count_lines(ts_files),
        "total_lines": count_lines(py_files) + count_lines(ts_files),
    }


# ── Construction du PDF ─────────────────────────────────────────────────────────

def _style(name: str, **kwargs) -> ParagraphStyle:
    base = getSampleStyleSheet()["Normal"]
    return ParagraphStyle(name, parent=base, **kwargs)


def _table_style(header_color=NAVY) -> TableStyle:
    return TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), header_color),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LGRAY]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ])


def build_pdf(output: Path, metrics: dict) -> None:
    doc = SimpleDocTemplate(
        str(output),
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )

    h1 = _style("H1", fontSize=20, textColor=NAVY, spaceAfter=4, fontName="Helvetica-Bold")
    h2 = _style("H2", fontSize=13, textColor=NAVY, spaceAfter=3, spaceBefore=10, fontName="Helvetica-Bold")
    body = _style("Body", fontSize=9, textColor=colors.HexColor("#334155"), spaceAfter=2)
    big = _style("Big", fontSize=36, textColor=CYAN, fontName="Helvetica-Bold", alignment=1)
    label = _style("Label", fontSize=8, textColor=GRAY, alignment=1)

    story = []
    now = datetime.now().strftime("%d/%m/%Y %H:%M")

    # ── En-tête ─────────────────────────────────────────────────────────────────
    story.append(Paragraph("Rapport Qualité — Cyber-Vault", h1))
    story.append(Paragraph(f"Généré le {now}", body))
    story.append(HRFlowable(width="100%", thickness=2, color=CYAN, spaceAfter=10))

    # ── Couverture ──────────────────────────────────────────────────────────────
    cov = metrics["coverage"]
    story.append(Paragraph("Couverture de tests", h2))
    pct = cov.get("percent", 0)
    pct_color = GREEN if pct >= 84 else (YELLOW if pct >= 70 else RED)
    pct_style = _style("Pct", fontSize=48, textColor=pct_color, fontName="Helvetica-Bold", alignment=1)
    story.append(Paragraph(f"{pct}%", pct_style))
    story.append(Paragraph("couverture globale", label))
    story.append(Spacer(1, 4 * mm))

    cov_table = Table([
        ["Lignes totales", "Lignes couvertes", "Lignes manquantes", "Seuil requis"],
        [
            str(cov.get("total", "—")),
            str(cov.get("covered", "—")),
            str(cov.get("missing", "—")),
            "84%",
        ],
    ], colWidths=[42 * mm] * 4)
    cov_table.setStyle(_table_style())
    story.append(cov_table)

    # ── Complexité ──────────────────────────────────────────────────────────────
    cmpl = metrics["complexity"]
    story.append(Paragraph("Complexité cyclomatique", h2))
    if cmpl.get("available"):
        cmpl_table = Table([
            ["Fonctions analysées", "Complexité moyenne", "Fonctions complexes (>10)"],
            [
                str(cmpl.get("total_functions", "—")),
                str(cmpl.get("average", "—")),
                str(cmpl.get("high_complexity_count", "—")),
            ],
        ], colWidths=[56 * mm] * 3)
        cmpl_table.setStyle(_table_style())
        story.append(cmpl_table)
        if cmpl.get("top10"):
            story.append(Spacer(1, 3 * mm))
            story.append(Paragraph("Top 10 fonctions les plus complexes", body))
            rows = [["Fonction", "Complexité", "Rang"]]
            for f in cmpl["top10"]:
                rank_color = RED if f["rank"] in ("D", "E", "F") else (YELLOW if f["rank"] == "C" else GREEN)
                rows.append([f["name"], str(f["complexity"]), f["rank"]])
            t = Table(rows, colWidths=[110 * mm, 30 * mm, 30 * mm])
            t.setStyle(_table_style())
            story.append(t)
    else:
        story.append(Paragraph("radon non disponible — installez-le avec : pip install radon", body))

    # ── Sécurité ────────────────────────────────────────────────────────────────
    story.append(Paragraph("Audit de sécurité", h2))
    bandit = metrics["bandit"]
    npm = metrics["npm_audit"]

    sec_rows = [["Outil", "Critique / Haute", "Moyenne", "Faible"]]
    if bandit.get("available"):
        sec_rows.append(["Bandit (Python)", str(bandit["high"]), str(bandit["medium"]), str(bandit["low"])])
    else:
        sec_rows.append(["Bandit (Python)", "—", "—", "—"])
    if npm.get("available"):
        sec_rows.append([
            "npm audit (Frontend)",
            f"{npm['critical']} / {npm['high']}",
            str(npm["moderate"]),
            str(npm["low"]),
        ])
    else:
        sec_rows.append(["npm audit (Frontend)", "—", "—", "—"])

    sec_table = Table(sec_rows, colWidths=[60 * mm, 45 * mm, 30 * mm, 30 * mm])
    sec_table.setStyle(_table_style())
    story.append(sec_table)

    # ── Statistiques de code ─────────────────────────────────────────────────────
    code = metrics["code_stats"]
    story.append(Paragraph("Statistiques de code", h2))
    code_rows = [
        ["Langage", "Fichiers", "Lignes de code"],
        ["Python (app)", str(code["python_files"]), str(code["python_lines"])],
        ["TypeScript (frontend)", str(code["typescript_files"]), str(code["typescript_lines"])],
        ["Total", str(code["python_files"] + code["typescript_files"]), str(code["total_lines"])],
    ]
    code_table = Table(code_rows, colWidths=[70 * mm, 40 * mm, 55 * mm])
    code_table.setStyle(_table_style())
    story.append(code_table)

    # ── Git ─────────────────────────────────────────────────────────────────────
    git = metrics["git_stats"]
    story.append(Paragraph("Historique Git", h2))
    git_rows = [
        ["Commits totaux", "Contributeurs", "Premier commit", "Dernier commit"],
        [
            git.get("total_commits", "—"),
            str(len(git.get("contributors", []))),
            git.get("first_commit", "—"),
            git.get("last_commit", "—"),
        ],
    ]
    git_table = Table(git_rows, colWidths=[42 * mm] * 4)
    git_table.setStyle(_table_style())
    story.append(git_table)

    if git.get("contributors"):
        story.append(Spacer(1, 2 * mm))
        story.append(Paragraph("Contributeurs : " + ", ".join(git["contributors"]), body))

    # ── Pied de page ─────────────────────────────────────────────────────────────
    story.append(Spacer(1, 8 * mm))
    story.append(HRFlowable(width="100%", thickness=1, color=GRAY))
    story.append(Paragraph(
        "Rapport généré automatiquement par scripts/generate_quality_report.py — Cyber-Vault",
        _style("Footer", fontSize=7, textColor=GRAY, alignment=1, spaceBefore=4),
    ))

    doc.build(story)


# ── Point d'entrée ──────────────────────────────────────────────────────────────

def main() -> None:
    if len(sys.argv) > 1:
        output = Path(sys.argv[1])
    else:
        reports_dir = ROOT / "reports"
        reports_dir.mkdir(exist_ok=True)
        output = reports_dir / f"quality-report-{datetime.now().strftime('%Y%m%d')}.pdf"

    print("Generation du rapport qualite Cyber-Vault...")
    print(f"Sortie : {output}\n")

    metrics = {
        "coverage": collect_coverage(),
        "complexity": collect_complexity(),
        "bandit": collect_bandit(),
        "npm_audit": collect_npm_audit(),
        "git_stats": collect_git_stats(),
        "code_stats": collect_code_stats(),
    }

    build_pdf(output, metrics)
    print(f"\nOK Rapport genere : {output}")


if __name__ == "__main__":
    main()
