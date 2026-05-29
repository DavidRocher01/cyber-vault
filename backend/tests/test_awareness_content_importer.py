"""
Tests d'intégration — ContentImporter (awareness module).

Couvre :
  - Import d'un programme avec modules depuis un répertoire YAML/Markdown
  - Comportement upsert (re-import sans duplication)
  - Répertoire programs/ absent
  - meta.yaml manquant pour un module
  - Module sans quiz (has_quiz=false)
  - Module référencé mais répertoire absent
  - Contenu Markdown et quiz YAML correctement persistés
"""

from pathlib import Path

import pytest
from sqlalchemy import select

from app.models.awareness_module import AwarenessModule
from app.models.awareness_program import AwarenessProgram
from app.services.awareness_content_importer import import_from_directory

# ── helpers ────────────────────────────────────────────────────────────────────


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _minimal_content(tmp_path: Path) -> Path:
    """Crée une structure minimale valide : 1 programme, 1 module avec quiz."""
    root = tmp_path / "content" / "fr"

    _write(
        root / "programs" / "test-prog.yaml",
        """
slug: test-prog
title: Programme Test
language: fr
version: "1.0"
estimated_duration_minutes: 5
passing_score: 60
certificate_validity_months: 12
is_active: true
modules:
  - module-a
""",
    )
    _write(
        root / "modules" / "module-a" / "meta.yaml",
        """
title: Module A
description: Description A
content_type: mixed
estimated_duration_minutes: 3
xp_points: 10
has_quiz: true
quiz_max_attempts: 3
quiz_cooldown_minutes: 15
quiz_passing_score: 60
is_active: true
""",
    )
    _write(root / "modules" / "module-a" / "content.md", "# Contenu\nTexte du module A.")
    _write(
        root / "modules" / "module-a" / "quiz.yaml",
        """
questions:
  - id: q1
    type: single_choice
    weight: 1
    text: "Question 1 ?"
    answers:
      - id: a
        text: "Réponse correcte"
        correct: true
      - id: b
        text: "Mauvaise réponse"
        correct: false
""",
    )
    return root


# ── import valide ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_import_creates_program(db_session, tmp_path):
    root = _minimal_content(tmp_path)
    summary = await import_from_directory(db_session, root)

    assert summary["errors"] == []
    assert summary["programs"] == 1

    result = await db_session.execute(
        select(AwarenessProgram).where(AwarenessProgram.slug == "test-prog")
    )
    prog = result.scalar_one_or_none()
    assert prog is not None
    assert prog.title == "Programme Test"
    assert prog.passing_score == 60
    assert prog.version == "1.0"


@pytest.mark.asyncio
async def test_import_creates_module(db_session, tmp_path):
    root = _minimal_content(tmp_path)
    summary = await import_from_directory(db_session, root)

    assert summary["modules"] == 1

    result = await db_session.execute(
        select(AwarenessModule).where(AwarenessModule.slug == "module-a")
    )
    mod = result.scalar_one_or_none()
    assert mod is not None
    assert mod.title == "Module A"
    assert mod.xp_points == 10
    assert mod.has_quiz is True


@pytest.mark.asyncio
async def test_import_persists_markdown_content(db_session, tmp_path):
    root = _minimal_content(tmp_path)
    await import_from_directory(db_session, root)

    result = await db_session.execute(
        select(AwarenessModule).where(AwarenessModule.slug == "module-a")
    )
    mod = result.scalar_one()
    assert "Contenu" in (mod.content_markdown or "")


@pytest.mark.asyncio
async def test_import_persists_quiz_yaml(db_session, tmp_path):
    root = _minimal_content(tmp_path)
    await import_from_directory(db_session, root)

    result = await db_session.execute(
        select(AwarenessModule).where(AwarenessModule.slug == "module-a")
    )
    mod = result.scalar_one()
    assert mod.quiz_yaml is not None
    assert "q1" in mod.quiz_yaml


@pytest.mark.asyncio
async def test_import_sets_position_from_program_order(db_session, tmp_path):
    """Le ContentImporter doit assigner position=1 au premier module."""
    root = _minimal_content(tmp_path)
    await import_from_directory(db_session, root)

    result = await db_session.execute(
        select(AwarenessModule).where(AwarenessModule.slug == "module-a")
    )
    mod = result.scalar_one()
    assert mod.position == 1


# ── upsert ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_reimport_does_not_duplicate(db_session, tmp_path):
    """Importer deux fois le même contenu → toujours 1 programme, 1 module."""
    root = _minimal_content(tmp_path)
    await import_from_directory(db_session, root)
    await import_from_directory(db_session, root)

    progs = (
        (
            await db_session.execute(
                select(AwarenessProgram).where(AwarenessProgram.slug == "test-prog")
            )
        )
        .scalars()
        .all()
    )
    mods = (
        (
            await db_session.execute(
                select(AwarenessModule).where(AwarenessModule.slug == "module-a")
            )
        )
        .scalars()
        .all()
    )

    assert len(progs) == 1
    assert len(mods) == 1


@pytest.mark.asyncio
async def test_reimport_updates_title(db_session, tmp_path):
    root = _minimal_content(tmp_path)
    await import_from_directory(db_session, root)

    # Modifier le titre dans le YAML
    prog_file = root / "programs" / "test-prog.yaml"
    content = prog_file.read_text(encoding="utf-8").replace(
        "title: Programme Test", "title: Programme Modifie"
    )
    prog_file.write_text(content, encoding="utf-8")
    await import_from_directory(db_session, root)

    result = await db_session.execute(
        select(AwarenessProgram).where(AwarenessProgram.slug == "test-prog")
    )
    prog = result.scalar_one()
    assert prog.title == "Programme Modifie"


# ── erreurs tolérées ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_missing_programs_dir_returns_error(db_session, tmp_path):
    root = tmp_path / "vide"
    root.mkdir()
    summary = await import_from_directory(db_session, root)

    assert summary["programs"] == 0
    assert len(summary["errors"]) == 1
    assert "programs/" in summary["errors"][0]


@pytest.mark.asyncio
async def test_missing_module_directory_reported(db_session, tmp_path):
    root = _minimal_content(tmp_path)
    # Référencer un module inexistant dans le programme
    prog_file = root / "programs" / "test-prog.yaml"
    content = prog_file.read_text(encoding="utf-8").replace(
        "modules:\n  - module-a", "modules:\n  - module-a\n  - module-ghost"
    )
    prog_file.write_text(content, encoding="utf-8")

    summary = await import_from_directory(db_session, root)
    assert summary["modules"] == 1  # module-a importé
    assert any("module-ghost" in e for e in summary["errors"])


@pytest.mark.asyncio
async def test_missing_meta_yaml_reported(db_session, tmp_path):
    root = _minimal_content(tmp_path)
    # Supprimer le meta.yaml
    (root / "modules" / "module-a" / "meta.yaml").unlink()

    summary = await import_from_directory(db_session, root)
    assert summary["modules"] == 0
    assert any("meta.yaml" in e for e in summary["errors"])


@pytest.mark.asyncio
async def test_module_without_quiz(db_session, tmp_path):
    root = _minimal_content(tmp_path)
    # Supprimer quiz.yaml et désactiver has_quiz
    (root / "modules" / "module-a" / "quiz.yaml").unlink()
    meta_file = root / "modules" / "module-a" / "meta.yaml"
    content = meta_file.read_text(encoding="utf-8").replace("has_quiz: true", "has_quiz: false")
    meta_file.write_text(content, encoding="utf-8")

    summary = await import_from_directory(db_session, root)
    assert summary["errors"] == []
    assert summary["modules"] == 1

    result = await db_session.execute(
        select(AwarenessModule).where(AwarenessModule.slug == "module-a")
    )
    mod = result.scalar_one()
    assert mod.has_quiz is False
    assert mod.quiz_yaml is None


# ── multi-modules ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_import_multiple_modules_in_order(db_session, tmp_path):
    root = tmp_path / "content" / "fr"

    _write(
        root / "programs" / "multi.yaml",
        """
slug: multi
title: Multi-modules
language: fr
version: "1.0"
estimated_duration_minutes: 10
passing_score: 60
certificate_validity_months: 12
is_active: true
modules:
  - mod-first
  - mod-second
""",
    )
    for slug in ("mod-first", "mod-second"):
        _write(
            root / "modules" / slug / "meta.yaml",
            f"""
title: {slug}
content_type: markdown
estimated_duration_minutes: 3
xp_points: 10
has_quiz: false
is_active: true
""",
        )
        _write(root / "modules" / slug / "content.md", f"# {slug}")

    summary = await import_from_directory(db_session, root)
    assert summary["modules"] == 2
    assert summary["errors"] == []

    first = (
        await db_session.execute(select(AwarenessModule).where(AwarenessModule.slug == "mod-first"))
    ).scalar_one()
    second = (
        await db_session.execute(
            select(AwarenessModule).where(AwarenessModule.slug == "mod-second")
        )
    ).scalar_one()

    assert first.position == 1
    assert second.position == 2
