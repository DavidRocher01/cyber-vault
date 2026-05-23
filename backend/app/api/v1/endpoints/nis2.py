"""
NIS2 Compliance endpoints — save/load user assessment and export PDF.
"""

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.nis2_assessment import Nis2Assessment
from app.services.assessment_service import compute_assessment_score

router = APIRouter(prefix="/nis2", tags=["nis2"])

# ---------------------------------------------------------------------------
# Valid statuses
# ---------------------------------------------------------------------------
VALID_STATUSES = {"compliant", "partial", "non_compliant", "na"}


# ---------------------------------------------------------------------------
# NIS2 items definition (single source of truth)
# ---------------------------------------------------------------------------
NIS2_CATEGORIES = [
    {
        "id": "governance",
        "label": "Gouvernance",
        "icon": "policy",
        "items": [
            {"id": "rssi",         "label": "Désignation d'un RSSI ou responsable cyber",            "desc": "Une personne identifiée est responsable de la sécurité des systèmes d'information."},
            {"id": "policy",       "label": "Politique de sécurité SI documentée et approuvée",      "desc": "Une politique formelle existe, est à jour et a été validée par la direction."},
            {"id": "mgmt_training","label": "Implication et formation de la direction",               "desc": "Les dirigeants ont été sensibilisés aux risques cyber et à leurs responsabilités NIS2."},
            {"id": "policy_review","label": "Revue annuelle de la politique de sécurité",             "desc": "La politique est révisée au moins une fois par an et après chaque incident majeur."},
        ],
    },
    {
        "id": "risk",
        "label": "Gestion des risques",
        "icon": "security",
        "items": [
            {"id": "risk_analysis",   "label": "Analyse de risques formelle (EBIOS RM / ISO 27005)", "desc": "Une analyse de risques structurée a été réalisée et documentée."},
            {"id": "risk_treatment",  "label": "Plan de traitement des risques avec suivi",           "desc": "Chaque risque identifié dispose d'un plan d'action suivi régulièrement."},
            {"id": "asset_inventory", "label": "Inventaire des actifs critiques",                     "desc": "Tous les systèmes, données et services critiques sont répertoriés."},
            {"id": "data_classif",    "label": "Classification des données",                          "desc": "Les données sont classifiées selon leur sensibilité (public, interne, confidentiel, secret)."},
        ],
    },
    {
        "id": "access",
        "label": "Sécurité des accès",
        "icon": "lock",
        "items": [
            {"id": "mfa",            "label": "MFA sur tous les accès critiques",             "desc": "L'authentification multi-facteurs est déployée sur les systèmes et comptes critiques."},
            {"id": "password_policy","label": "Politique de mots de passe robuste",           "desc": "Longueur minimale 12 caractères, complexité, renouvellement, pas de réutilisation."},
            {"id": "pam",            "label": "Gestion des comptes à privilèges (PAM)",       "desc": "Les accès administrateurs sont tracés, justifiés et revus régulièrement."},
            {"id": "access_review",  "label": "Revue périodique des droits d'accès",          "desc": "Les droits sont revus au minimum trimestriellement et lors de changements RH."},
        ],
    },
    {
        "id": "systems",
        "label": "Sécurité des systèmes",
        "icon": "computer",
        "items": [
            {"id": "patch_mgmt",   "label": "Gestion des correctifs (patch critique < 72h)",  "desc": "Un processus formel garantit l'application rapide des correctifs de sécurité critiques."},
            {"id": "encryption",   "label": "Chiffrement des données sensibles (transit + repos)", "desc": "TLS 1.2+ en transit, chiffrement au repos pour les données sensibles."},
            {"id": "hardening",    "label": "Configuration sécurisée des systèmes",           "desc": "Les systèmes sont configurés selon des référentiels de durcissement (CIS Benchmarks, ANSSI)."},
            {"id": "edr",          "label": "Antivirus / EDR sur tous les postes",            "desc": "Une solution de détection d'endpoint est déployée et maintenue à jour."},
        ],
    },
    {
        "id": "incidents",
        "label": "Gestion des incidents",
        "icon": "warning",
        "items": [
            {"id": "incident_proc",   "label": "Procédure de détection et réponse documentée",    "desc": "Une procédure formelle de réponse aux incidents est documentée et connue des équipes."},
            {"id": "soc",             "label": "CERT/SOC ou capacité de surveillance",             "desc": "Une capacité de détection et de réponse aux incidents est opérationnelle."},
            {"id": "anssi_notif",     "label": "Notification ANSSI sous 24h (incidents significatifs)", "desc": "Le processus de notification à l'ANSSI est connu et testé."},
            {"id": "post_mortem",     "label": "Post-mortem et retour d'expérience",               "desc": "Chaque incident donne lieu à un rapport d'analyse et des actions correctives."},
        ],
    },
    {
        "id": "continuity",
        "label": "Continuité d'activité",
        "icon": "restore",
        "items": [
            {"id": "pca",     "label": "Plan de continuité (PCA) documenté et testé",          "desc": "Un PCA existe, est tenu à jour et a été testé lors d'un exercice."},
            {"id": "pra",     "label": "Plan de reprise (PRA) avec RTO/RPO définis",            "desc": "Les objectifs de reprise (délai et point de reprise) sont formalisés et atteignables."},
            {"id": "backups", "label": "Sauvegardes testées et déconnectées du réseau",         "desc": "Les sauvegardes sont régulières, chiffrées, testées, et au moins une copie est hors ligne."},
        ],
    },
    {
        "id": "supply_chain",
        "label": "Chaîne d'approvisionnement",
        "icon": "account_tree",
        "items": [
            {"id": "vendor_audit",     "label": "Évaluation sécurité des fournisseurs critiques",   "desc": "Les fournisseurs ayant accès aux SI critiques font l'objet d'une évaluation de sécurité."},
            {"id": "vendor_contracts", "label": "Clauses de sécurité dans les contrats fournisseurs","desc": "Les contrats incluent des exigences de sécurité, de notification d'incidents et d'audit."},
            {"id": "sca",              "label": "Inventaire des dépendances logicielles (SCA)",     "desc": "Les composants open source et tiers sont inventoriés et surveillés pour les vulnérabilités."},
        ],
    },
    {
        "id": "network",
        "label": "Sécurité réseau",
        "icon": "hub",
        "items": [
            {"id": "segmentation", "label": "Segmentation réseau (isolation des systèmes critiques)", "desc": "Les systèmes critiques sont isolés dans des zones réseau distinctes avec contrôle des flux."},
            {"id": "ids",          "label": "Surveillance des flux réseau (IDS/IPS)",                 "desc": "Une solution de détection d'intrusion surveille les flux réseau en continu."},
            {"id": "vpn",          "label": "VPN sécurisé pour les accès distants",                   "desc": "Tous les accès distants passent par un VPN avec authentification forte."},
        ],
    },
    {
        "id": "training",
        "label": "Formation & sensibilisation",
        "icon": "school",
        "items": [
            {"id": "awareness",       "label": "Programme de formation cyber pour les employés",  "desc": "Tous les employés suivent une formation annuelle de sensibilisation à la cybersécurité."},
            {"id": "phishing_sim",    "label": "Exercices de phishing simulé",                    "desc": "Des campagnes de phishing simulé sont menées régulièrement pour évaluer la vigilance."},
            {"id": "it_training",     "label": "Formation spécifique pour l'équipe IT/sécurité",  "desc": "L'équipe technique reçoit des formations adaptées aux menaces actuelles."},
        ],
    },
    {
        "id": "compliance",
        "label": "Enregistrement & conformité",
        "icon": "verified",
        "items": [
            {"id": "anssi_registration", "label": "Enregistrement sur le portail ANSSI",        "desc": "L'entité est enregistrée sur monespacenis2.anssi.fr (obligatoire pour les entités concernées)."},
            {"id": "annual_audit",       "label": "Audit de conformité annuel",                  "desc": "Un audit interne ou externe de conformité NIS2 est réalisé chaque année."},
        ],
    },
]

# Pre-compute flat item list for validation
ALL_ITEM_IDS = {item["id"] for cat in NIS2_CATEGORIES for item in cat["items"]}



# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class Nis2SaveIn(BaseModel):
    items: dict[str, str]  # { item_id: status }


class Nis2Out(BaseModel):
    items: dict[str, str]
    score: int
    updated_at: datetime | None
    categories: list  # static definition returned for convenience

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/me", response_model=Nis2Out)
async def get_assessment(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Nis2Assessment).where(Nis2Assessment.user_id == current_user.id)
    )
    assessment = result.scalar_one_or_none()
    items = json.loads(assessment.items_json) if assessment else {}
    score = assessment.score if assessment else 0
    updated_at = assessment.updated_at if assessment else None
    return {"items": items, "score": score, "updated_at": updated_at, "categories": NIS2_CATEGORIES}


@router.put("/me", response_model=Nis2Out)
async def save_assessment(
    payload: Nis2SaveIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Validate statuses
    for item_id, status in payload.items.items():
        if item_id not in ALL_ITEM_IDS:
            raise HTTPException(status_code=422, detail=f"Identifiant inconnu : {item_id}")
        if status not in VALID_STATUSES:
            raise HTTPException(status_code=422, detail=f"Statut invalide : {status}")

    score = compute_assessment_score(payload.items, ALL_ITEM_IDS)
    now = datetime.now(timezone.utc)

    result = await db.execute(
        select(Nis2Assessment).where(Nis2Assessment.user_id == current_user.id)
    )
    assessment = result.scalar_one_or_none()

    if assessment:
        assessment.items_json = json.dumps(payload.items)
        assessment.score = score
        assessment.updated_at = now
    else:
        assessment = Nis2Assessment(
            user_id=current_user.id,
            items_json=json.dumps(payload.items),
            score=score,
            created_at=now,
            updated_at=now,
        )
        db.add(assessment)

    await db.commit()
    await db.refresh(assessment)
    return {"items": payload.items, "score": score, "updated_at": assessment.updated_at, "categories": NIS2_CATEGORIES}


@router.get("/me/pdf")
async def export_assessment_pdf(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a NIS2 compliance report PDF."""
    result = await db.execute(
        select(Nis2Assessment).where(Nis2Assessment.user_id == current_user.id)
    )
    assessment = result.scalar_one_or_none()
    items = json.loads(assessment.items_json) if assessment else {}
    score = compute_assessment_score(items, ALL_ITEM_IDS)  # recalcul avec la formule corrigée (34 items)
    updated_at = assessment.updated_at if assessment else None

    from app.services.nis2_pdf import generate_nis2_pdf
    pdf_bytes = generate_nis2_pdf(
        categories=NIS2_CATEGORIES,
        items=items,
        score=score,
        updated_at=updated_at,
        user_email=current_user.email,
    )

    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="cyberscan_nis2_conformite.pdf"'},
    )
