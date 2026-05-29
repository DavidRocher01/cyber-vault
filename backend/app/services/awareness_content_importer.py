"""
ContentImporter — synchronise les programmes et modules depuis des fichiers YAML/Markdown.

Structure attendue du repo de contenu :
    content/
    └── fr/
        ├── programs/
        │   └── nis2-essentiel.yaml      ← définition du programme
        └── modules/
            └── phishing-bases/
                ├── meta.yaml            ← métadonnées du module
                ├── content.md           ← corps du module (Markdown)
                └── quiz.yaml            ← questions du quiz

Usage:
    from app.services.awareness_content_importer import import_from_directory
    await import_from_directory(db, Path("content/fr"))
"""

from __future__ import annotations

from pathlib import Path

import yaml
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.awareness_module import AwarenessModule
from app.models.awareness_program import AwarenessProgram


async def import_program(db: AsyncSession, data: dict) -> AwarenessProgram:
    """Upsert a program from its YAML definition."""
    slug = data["slug"]
    result = await db.execute(select(AwarenessProgram).where(AwarenessProgram.slug == slug))
    program = result.scalar_one_or_none()

    if program is None:
        program = AwarenessProgram(slug=slug)
        db.add(program)

    program.title = data["title"]
    program.description = data.get("description")
    program.language = data.get("language", "fr")
    program.estimated_duration_minutes = data.get("estimated_duration_minutes", 0)
    program.passing_score = data.get("passing_score", 60)
    program.certificate_validity_months = data.get("certificate_validity_months", 12)
    program.is_active = data.get("is_active", True)
    program.version = data.get("version", "1.0")

    await db.flush()
    return program


async def import_module(
    db: AsyncSession,
    program: AwarenessProgram,
    slug: str,
    meta: dict,
    content_md: str | None,
    quiz_yaml: str | None,
) -> AwarenessModule:
    """Upsert a module belonging to a program."""
    result = await db.execute(
        select(AwarenessModule).where(
            AwarenessModule.program_id == program.id,
            AwarenessModule.slug == slug,
        )
    )
    module = result.scalar_one_or_none()

    if module is None:
        module = AwarenessModule(program_id=program.id, slug=slug)
        db.add(module)

    module.title = meta["title"]
    module.description = meta.get("description")
    module.position = meta.get("position", 0)
    module.content_type = meta.get("content_type", "mixed")
    module.video_url = meta.get("video_url")
    module.slides_url = meta.get("slides_url")
    module.content_markdown = content_md
    module.estimated_duration_minutes = meta.get("estimated_duration_minutes", 5)
    module.xp_points = meta.get("xp_points", 10)
    module.has_quiz = meta.get("has_quiz", quiz_yaml is not None)
    module.quiz_yaml = quiz_yaml
    module.quiz_max_attempts = meta.get("quiz_max_attempts", 3)
    module.quiz_cooldown_minutes = meta.get("quiz_cooldown_minutes", 15)
    module.quiz_passing_score = meta.get("quiz_passing_score", 60)
    module.is_active = meta.get("is_active", True)

    await db.flush()
    return module


async def import_from_directory(db: AsyncSession, content_dir: Path) -> dict:
    """
    Scan content_dir for programs and modules, upsert all into the DB.

    Returns a summary dict: {"programs": N, "modules": N, "errors": [...]}
    """
    summary = {"programs": 0, "modules": 0, "errors": []}

    programs_dir = content_dir / "programs"
    modules_dir = content_dir / "modules"

    if not programs_dir.exists():
        summary["errors"].append(f"programs/ directory not found in {content_dir}")
        return summary

    # ── Import programs ────────────────────────────────────────────────────────
    for program_file in sorted(programs_dir.glob("*.yaml")):
        try:
            data = yaml.safe_load(program_file.read_text(encoding="utf-8"))
            program = await import_program(db, data)
            summary["programs"] += 1

            # ── Import modules listed in the program YAML ──────────────────────
            for position, module_slug in enumerate(data.get("modules", []), start=1):
                module_dir = modules_dir / module_slug
                if not module_dir.exists():
                    summary["errors"].append(f"Module directory not found: {module_dir}")
                    continue
                try:
                    meta_file = module_dir / "meta.yaml"
                    if not meta_file.exists():
                        summary["errors"].append(f"meta.yaml missing for module: {module_slug}")
                        continue

                    meta = yaml.safe_load(meta_file.read_text(encoding="utf-8"))
                    meta.setdefault("position", position)

                    content_md = None
                    content_file = module_dir / "content.md"
                    if content_file.exists():
                        content_md = content_file.read_text(encoding="utf-8")

                    quiz_yaml = None
                    quiz_file = module_dir / "quiz.yaml"
                    if quiz_file.exists():
                        quiz_yaml = quiz_file.read_text(encoding="utf-8")

                    await import_module(db, program, module_slug, meta, content_md, quiz_yaml)
                    summary["modules"] += 1
                except Exception as exc:
                    summary["errors"].append(f"Module {module_slug}: {exc}")

        except Exception as exc:
            summary["errors"].append(f"Program {program_file.name}: {exc}")

    await db.commit()
    return summary
