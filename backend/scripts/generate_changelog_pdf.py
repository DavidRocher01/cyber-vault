"""
Generate a changelog PDF from git log.
Usage:
  python scripts/generate_changelog_pdf.py [--since TAG_OR_DATE] [--tag CURRENT_TAG] [--out FILE]
"""

from __future__ import annotations

import argparse
import io
import re
import subprocess
from collections import defaultdict
from datetime import datetime, timedelta

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

NAVY = colors.HexColor("#0f172a")
CYAN = colors.HexColor("#06b6d4")
GREEN = colors.HexColor("#22c55e")
PURPLE = colors.HexColor("#8b5cf6")
YELLOW = colors.HexColor("#f59e0b")
RED = colors.HexColor("#ef4444")
GRAY = colors.HexColor("#64748b")
LGRAY = colors.HexColor("#f1f5f9")
BORDER = colors.HexColor("#cbd5e1")
WHITE = colors.white
BLACK = colors.HexColor("#1e293b")

COMMIT_TYPES = {
    "feat": ("Nouvelles fonctionnalités", GREEN),
    "fix": ("Corrections de bugs", RED),
    "security": ("Sécurité", RED),
    "perf": ("Performances", CYAN),
    "refactor": ("Refactoring", PURPLE),
    "test": ("Tests", YELLOW),
    "docs": ("Documentation", GRAY),
    "ci": ("CI / Déploiement", CYAN),
    "build": ("Build", GRAY),
    "chore": ("Maintenance", GRAY),
    "other": ("Autres", GRAY),
}


def _p(text: str, **kw) -> Paragraph:
    return Paragraph(text, ParagraphStyle("_", **kw))


def get_last_tag() -> str | None:
    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0", "HEAD~1"],
            capture_output=True,
            text=True,
        )
        return result.stdout.strip() or None
    except Exception:
        return None


def get_commits(since: str | None) -> list[dict]:
    if since:
        ref = f"{since}.." if not since.startswith("20") else f"--since={since}"
        if since.startswith("v") or re.match(r"^\d+\.\d+", since):
            cmd = [
                "git",
                "log",
                f"{since}..",
                "--pretty=format:%H%x00%s%x00%an%x00%ad",
                "--date=short",
            ]
        else:
            cmd = [
                "git",
                "log",
                f"--since={since}",
                "--pretty=format:%H%x00%s%x00%an%x00%ad",
                "--date=short",
            ]
    else:
        since_date = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d")
        cmd = [
            "git",
            "log",
            f"--since={since_date}",
            "--pretty=format:%H%x00%s%x00%an%x00%ad",
            "--date=short",
        ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    commits = []
    for line in result.stdout.strip().splitlines():
        parts = line.split("\x00")
        if len(parts) == 4:
            commits.append(
                {
                    "hash": parts[0][:7],
                    "subject": parts[1],
                    "author": parts[2],
                    "date": parts[3],
                }
            )
    return commits


def classify(commits: list[dict]) -> dict[str, list[dict]]:
    groups: dict[str, list] = defaultdict(list)
    pattern = re.compile(r"^(\w+)(?:\([\w/-]+\))?!?:\s*(.*)")
    for c in commits:
        m = pattern.match(c["subject"])
        if m:
            typ = m.group(1).lower()
            c = {**c, "message": m.group(2)}
            key = typ if typ in COMMIT_TYPES else "other"
        else:
            c = {**c, "message": c["subject"]}
            key = "other"
        groups[key].append(c)
    return dict(groups)


def build_pdf(groups: dict, tag: str, since: str | None, out_path: str) -> None:
    buf = io.BytesIO()
    W, _ = A4
    mg = 16 * mm
    cw = W - 2 * mg
    half = cw / 2 - 3 * mm
    gap = 6 * mm
    now = datetime.utcnow().strftime("%d/%m/%Y")

    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=mg,
        rightMargin=mg,
        topMargin=14 * mm,
        bottomMargin=16 * mm,
    )
    s = []

    # ── En-tête ──────────────────────────────────────────────────────────────
    brand = Table(
        [
            [
                _p(
                    "<b>Rocher Cybersécurité</b>",
                    fontSize=18,
                    fontName="Helvetica-Bold",
                    textColor=WHITE,
                    leading=22,
                ),
                _p(
                    "<font color='#06b6d4'>●</font>",
                    fontSize=24,
                    fontName="Helvetica-Bold",
                    textColor=CYAN,
                    alignment=2,
                ),
            ]
        ],
        colWidths=[half * 0.7, half * 0.3],
    )
    brand.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), NAVY),
                ("TOPPADDING", (0, 0), (-1, -1), 12),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                ("LEFTPADDING", (0, 0), (-1, -1), 14),
                ("RIGHTPADDING", (0, 0), (-1, -1), 14),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )

    title_label = f"CHANGELOG — {tag}" if tag and tag != "" else "CHANGELOG"
    title_box = Table(
        [
            [
                _p(
                    f"<b>{title_label}</b>",
                    fontSize=14,
                    fontName="Helvetica-Bold",
                    textColor=NAVY,
                    alignment=2,
                ),
            ]
        ],
        colWidths=[half],
    )
    title_box.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 1.5, NAVY),
                ("TOPPADDING", (0, 0), (-1, -1), 12),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )

    top_row = Table([[brand, "", title_box]], colWidths=[half, gap, half])
    top_row.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    s.append(top_row)
    s.append(Spacer(1, 3 * mm))

    since_label = f"Depuis {since}" if since else "30 derniers jours"
    s.append(
        _p(
            f"<font color='#64748b'>Généré le</font> <b>{now}</b>  —  "
            f"<font color='#64748b'>{since_label}</font>  —  "
            f"<font color='#64748b'>{sum(len(v) for v in groups.values())} commit(s)</font>",
            fontSize=8,
            fontName="Helvetica",
            textColor=BLACK,
            alignment=2,
        )
    )
    s.append(Spacer(1, 5 * mm))
    s.append(HRFlowable(width=cw, thickness=0.6, color=BORDER, spaceAfter=5 * mm))

    if not groups:
        s.append(
            _p(
                "Aucun commit trouvé pour cette période.",
                fontSize=10,
                fontName="Helvetica",
                textColor=GRAY,
            )
        )
    else:
        for typ_key in COMMIT_TYPES:
            if typ_key not in groups:
                continue
            commits = groups[typ_key]
            label, type_color = COMMIT_TYPES[typ_key]

            # Section header
            header_tbl = Table(
                [
                    [
                        _p(
                            f"<b>{label}</b>",
                            fontSize=9,
                            fontName="Helvetica-Bold",
                            textColor=WHITE,
                        ),
                        _p(
                            f"{len(commits)}",
                            fontSize=9,
                            fontName="Helvetica-Bold",
                            textColor=WHITE,
                            alignment=2,
                        ),
                    ]
                ],
                colWidths=[cw * 0.88, cw * 0.12],
            )
            header_tbl.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), type_color),
                        ("TOPPADDING", (0, 0), (-1, -1), 6),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                        ("LEFTPADDING", (0, 0), (-1, -1), 10),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ]
                )
            )
            s.append(header_tbl)

            # Commits rows
            rows = []
            tstyle = [
                ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
                ("LINEBELOW", (0, 0), (-1, -1), 0.3, BORDER),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
            for i, c in enumerate(commits):
                bg = WHITE if i % 2 == 0 else colors.HexColor("#f8fafc")
                tstyle.append(("BACKGROUND", (0, i), (-1, i), bg))
                rows.append(
                    [
                        _p(
                            f"<font color='#64748b'><b>{c['hash']}</b></font>",
                            fontSize=7,
                            fontName="Helvetica-Bold",
                            textColor=GRAY,
                        ),
                        _p(
                            c["message"],
                            fontSize=7.5,
                            fontName="Helvetica",
                            textColor=BLACK,
                        ),
                        _p(
                            c["date"],
                            fontSize=7,
                            fontName="Helvetica",
                            textColor=GRAY,
                            alignment=2,
                        ),
                    ]
                )

            tbl = Table(rows, colWidths=[cw * 0.08, cw * 0.73, cw * 0.19])
            tbl.setStyle(TableStyle(tstyle))
            s.append(tbl)
            s.append(Spacer(1, 5 * mm))

    # ── Pied de page ─────────────────────────────────────────────────────────
    s.append(HRFlowable(width=cw, thickness=0.5, color=BORDER, spaceAfter=3 * mm))
    s.append(
        _p(
            f"Rocher Cybersécurité — Changelog automatique — {now} — cyberscanapp.com",
            fontSize=7,
            fontName="Helvetica",
            textColor=GRAY,
            alignment=1,
        )
    )

    doc.build(s)
    with open(out_path, "wb") as f:
        f.write(buf.getvalue())
    print(f"PDF généré : {out_path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--since", default="")
    parser.add_argument("--tag", default="")
    parser.add_argument("--out", default="changelog.pdf")
    args = parser.parse_args()

    since = args.since.strip() or None
    tag = args.tag.strip() or None

    if since is None and tag:
        # Use previous tag as since reference
        last = get_last_tag()
        since = last

    print(f"Récupération des commits (depuis: {since or '30 derniers jours'})…")
    commits = get_commits(since)
    print(f"  {len(commits)} commit(s) trouvés")

    groups = classify(commits)
    build_pdf(groups, tag or "", since, args.out)


if __name__ == "__main__":
    main()
