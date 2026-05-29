"""
Validates the structure of awareness content files (YAML + Markdown).

Usage: python scripts/validate_awareness_content.py
Returns exit code 0 on success, 1 on failure.
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

import yaml

# Force UTF-8 output (avoids cp1252 issues on Windows)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

CONTENT_DIR = Path(__file__).parent.parent.parent / "content" / "fr"
MODULES_DIR = CONTENT_DIR / "modules"
PROGRAMS_DIR = CONTENT_DIR / "programs"

META_REQUIRED_FIELDS = {
    "title": str,
    "description": str,
    "estimated_duration_minutes": int,
    "xp_points": int,
    "has_quiz": bool,
    "quiz_max_attempts": int,
    "quiz_passing_score": int,
    "is_active": bool,
}

QUIZ_QUESTION_REQUIRED = {"id", "type", "text", "answers"}
VALID_QUESTION_TYPES = {"single_choice", "multiple_choice", "true_false"}

errors: list[str] = []


def err(msg: str) -> None:
    errors.append(msg)
    print(f"  [FAIL] {msg}")


def ok(msg: str) -> None:
    print(f"  [OK]   {msg}")


def validate_module(module_dir: Path) -> None:
    slug = module_dir.name
    print(f"\n[{slug}]")

    # ── meta.yaml ────────────────────────────────────────────────────────────
    meta_path = module_dir / "meta.yaml"
    if not meta_path.exists():
        err("meta.yaml manquant")
        return

    try:
        meta = yaml.safe_load(meta_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        err(f"meta.yaml invalide : {e}")
        return

    for field, expected_type in META_REQUIRED_FIELDS.items():
        if field not in meta:
            err(f"meta.yaml : champ '{field}' manquant")
        elif not isinstance(meta[field], expected_type):
            err(
                f"meta.yaml : '{field}' doit être {expected_type.__name__}, trouvé {type(meta[field]).__name__}"
            )

    if meta.get("estimated_duration_minutes", 0) < 1:
        err("meta.yaml : estimated_duration_minutes doit être >= 1")

    ok("meta.yaml valide")

    # ── content.md ────────────────────────────────────────────────────────────
    content_path = module_dir / "content.md"
    if not content_path.exists():
        err("content.md manquant")
    else:
        content = content_path.read_text(encoding="utf-8").strip()
        if len(content) < 200:
            err(f"content.md trop court ({len(content)} chars, minimum 200)")
        elif not content.startswith("#"):
            err("content.md doit commencer par un titre Markdown (#)")
        else:
            ok(f"content.md valide ({len(content)} chars)")

    # ── quiz.yaml ─────────────────────────────────────────────────────────────
    if not meta.get("has_quiz", False):
        ok("quiz ignoré (has_quiz: false)")
        return

    quiz_path = module_dir / "quiz.yaml"
    if not quiz_path.exists():
        err("quiz.yaml manquant (has_quiz: true)")
        return

    try:
        quiz = yaml.safe_load(quiz_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        err(f"quiz.yaml invalide : {e}")
        return

    questions = quiz.get("questions", [])
    if not questions:
        err("quiz.yaml : aucune question trouvée")
        return

    if len(questions) < 6:
        err(f"quiz.yaml : seulement {len(questions)} questions (minimum recommandé : 6)")

    ids_seen: set[str] = set()
    for i, q in enumerate(questions):
        prefix = f"quiz.yaml question #{i + 1}"

        missing = QUIZ_QUESTION_REQUIRED - set(q.keys())
        if missing:
            err(f"{prefix} : champs manquants {missing}")
            continue

        if q["id"] in ids_seen:
            err(f"{prefix} : id '{q['id']}' en doublon")
        ids_seen.add(q["id"])

        if q["type"] not in VALID_QUESTION_TYPES:
            err(f"{prefix} : type '{q['type']}' invalide (attendu : {VALID_QUESTION_TYPES})")

        answers = q.get("answers", [])
        if len(answers) < 2:
            err(f"{prefix} : moins de 2 réponses")

        correct_count = sum(1 for a in answers if a.get("correct", False))
        if correct_count == 0:
            err(f"{prefix} : aucune réponse correcte")
        if q["type"] == "single_choice" and correct_count > 1:
            err(f"{prefix} : single_choice mais {correct_count} réponses correctes")

        for a in answers:
            if "id" not in a or "text" not in a:
                err(f"{prefix} : réponse sans 'id' ou 'text'")

    ok(f"quiz.yaml valide ({len(questions)} questions)")


def validate_program(program_path: Path) -> None:
    slug = program_path.stem
    print(f"\n[programme: {slug}]")

    try:
        prog = yaml.safe_load(program_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        err(f"{program_path.name} invalide : {e}")
        return

    for field in ("slug", "title", "estimated_duration_minutes", "modules"):
        if field not in prog:
            err(f"{program_path.name} : champ '{field}' manquant")

    module_slugs = {d.name for d in MODULES_DIR.iterdir() if d.is_dir()}
    for module_slug in prog.get("modules", []):
        if module_slug not in module_slugs:
            err(
                f"programme '{slug}' référence le module '{module_slug}' introuvable dans {MODULES_DIR}"
            )
        else:
            ok(f"module '{module_slug}' référencé et présent")


def main() -> int:
    print("=== Validation des modules de sensibilisation ===\n")

    if not MODULES_DIR.exists():
        print(f"ERREUR : répertoire {MODULES_DIR} introuvable")
        return 1

    for module_dir in sorted(MODULES_DIR.iterdir()):
        if module_dir.is_dir():
            validate_module(module_dir)

    print("\n=== Validation des programmes ===")
    for program_path in sorted(PROGRAMS_DIR.glob("*.yaml")):
        validate_program(program_path)

    print(f"\n{'=' * 50}")
    if errors:
        print(f"ECHEC — {len(errors)} erreur(s) détectée(s) :")
        for e in errors:
            print(f"  • {e}")
        return 1
    else:
        print("SUCCES — tous les modules sont valides.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
