"""Endpoints CRUD des programmes (Sprint 3)."""

from __future__ import annotations

from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_learner, get_current_user
from app.models.awareness_learner import AwarenessLearner
from app.models.user import User
from app.schemas.awareness import AwarenessModuleOut, AwarenessProgramOut
from app.services import awareness_program_service

router = APIRouter()


# ── helpers ────────────────────────────────────────────────────────────────────


async def _build_programs_out(programs: list, db: AsyncSession) -> list[AwarenessProgramOut]:
    """Charge tous les modules actifs en une seule requête et construit les AwarenessProgramOut."""
    if not programs:
        return []
    program_ids = [p.id for p in programs]
    all_mods = await awareness_program_service.list_active_modules(db, program_ids)

    mods_by_program: dict[int, list] = defaultdict(list)
    for mod in all_mods:
        mods_by_program[mod.program_id].append(mod)

    out = []
    for prog in programs:
        prog_dict = {k: v for k, v in prog.__dict__.items() if not k.startswith("_")}
        prog_dict["modules"] = [
            AwarenessModuleOut.model_validate(m) for m in mods_by_program[prog.id]
        ]
        out.append(AwarenessProgramOut.model_validate(prog_dict))
    return out


# ── Programmes ─────────────────────────────────────────────────────────────────


@router.get("/admin/programs", response_model=list[AwarenessProgramOut])
async def list_programs_admin(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[AwarenessProgramOut]:
    """Liste les programmes actifs (accès consultant authentifié)."""
    programs = await awareness_program_service.list_active_programs(db)
    return await _build_programs_out(programs, db)


@router.get("/programs", response_model=list[AwarenessProgramOut])
async def list_programs(
    learner: AwarenessLearner = Depends(get_current_learner),
    db: AsyncSession = Depends(get_db),
) -> list[AwarenessProgramOut]:
    """Liste les programmes actifs disponibles pour un learner."""
    programs = await awareness_program_service.list_active_programs(db)
    return await _build_programs_out(programs, db)


@router.get("/programs/{program_id}", response_model=AwarenessProgramOut)
async def get_program(
    program_id: int,
    learner: AwarenessLearner = Depends(get_current_learner),
    db: AsyncSession = Depends(get_db),
) -> AwarenessProgramOut:
    prog = await awareness_program_service.get_active_program(db, program_id)
    if prog is None:
        raise HTTPException(status_code=404, detail="Programme introuvable.")
    result = await _build_programs_out([prog], db)
    return result[0]
