"""
ISO 27001:2022 Compliance endpoints — save/load user assessment and export PDF.
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
from app.models.iso27001_assessment import Iso27001Assessment

router = APIRouter(prefix="/iso27001", tags=["iso27001"])

# ---------------------------------------------------------------------------
# Valid statuses
# ---------------------------------------------------------------------------
VALID_STATUSES = {"compliant", "partial", "non_compliant", "na"}


# ---------------------------------------------------------------------------
# ISO 27001:2022 items definition (single source of truth)
# Basé sur la norme ISO/IEC 27001:2022 — Clauses 4-10 + Annexe A
# ---------------------------------------------------------------------------
ISO27001_CATEGORIES = [
    {
        "id": "context",
        "label": "Contexte & Gouvernance",
        "icon": "policy",
        "items": [
            {"id": "scope",          "label": "Périmètre du SMSI défini et documenté",                   "desc": "Le champ d'application du Système de Management de la Sécurité de l'Information est formalisé (Clause 4.3)."},
            {"id": "isms_policy",    "label": "Politique de sécurité de l'information approuvée",         "desc": "Une politique SMSI signée par la direction existe, est communiquée et régulièrement révisée (Clause 5.2)."},
            {"id": "roles",          "label": "Responsabilités et autorités définies",                    "desc": "Les rôles SMSI (RSSI, propriétaires d'actifs) sont nommés et leurs responsabilités documentées (Clause 5.3)."},
            {"id": "mgmt_review",    "label": "Revue de direction annuelle du SMSI",                      "desc": "La direction réalise une revue formelle du SMSI au moins une fois par an (Clause 9.3)."},
            {"id": "internal_audit", "label": "Audit interne SMSI planifié et réalisé",                   "desc": "Des audits internes sont planifiés, réalisés et documentés avec suivi des écarts (Clause 9.2)."},
        ],
    },
    {
        "id": "risk",
        "label": "Gestion des risques",
        "icon": "security",
        "items": [
            {"id": "risk_method",    "label": "Méthode d'évaluation des risques documentée",              "desc": "Une méthodologie formelle d'identification et d'évaluation des risques SI est définie (Clause 6.1.2)."},
            {"id": "risk_register",  "label": "Registre des risques maintenu à jour",                     "desc": "Tous les risques identifiés sont enregistrés avec propriétaire, niveau et traitement associé."},
            {"id": "risk_treatment", "label": "Plan de traitement des risques avec suivi",                 "desc": "Chaque risque a un plan d'action suivi, avec décision d'acceptation, mitigation, transfert ou refus (Clause 6.1.3)."},
            {"id": "soa",            "label": "Déclaration d'applicabilité (SoA) rédigée",                "desc": "La SoA liste tous les contrôles Annexe A avec justification d'inclusion ou d'exclusion (Clause 6.1.3d)."},
        ],
    },
    {
        "id": "assets",
        "label": "Gestion des actifs",
        "icon": "inventory_2",
        "items": [
            {"id": "asset_inv",      "label": "Inventaire des actifs informationnels tenu à jour",        "desc": "Tous les actifs (matériels, logiciels, données, services) sont inventoriés avec propriétaire (A.5.9)."},
            {"id": "data_classif",   "label": "Classification et étiquetage des informations",            "desc": "Les informations sont classifiées (public, interne, confidentiel, secret) et étiquetées (A.5.12 / A.5.13)."},
            {"id": "media_disposal", "label": "Procédure de suppression sécurisée des supports",          "desc": "Les supports contenant des données sensibles sont effacés ou détruits de façon sécurisée avant réutilisation (A.7.14)."},
        ],
    },
    {
        "id": "access",
        "label": "Contrôle des accès",
        "icon": "lock",
        "items": [
            {"id": "access_policy",  "label": "Politique de contrôle des accès documentée",               "desc": "Les règles d'attribution, de révision et de révocation des accès sont formalisées (A.5.15)."},
            {"id": "mfa",            "label": "Authentification multi-facteurs sur les accès critiques",   "desc": "Le MFA est imposé pour les accès aux systèmes et données sensibles (A.8.5)."},
            {"id": "pam",            "label": "Gestion des comptes à privilèges (PAM)",                    "desc": "Les accès administrateurs sont tracés, limités au strict nécessaire et revus régulièrement (A.8.2)."},
            {"id": "access_review",  "label": "Revue périodique des droits d'accès",                      "desc": "Les droits d'accès sont revus au minimum tous les trimestres et lors de changements RH (A.5.18)."},
        ],
    },
    {
        "id": "crypto",
        "label": "Cryptographie",
        "icon": "enhanced_encryption",
        "items": [
            {"id": "crypto_policy",  "label": "Politique d'utilisation de la cryptographie",              "desc": "Une politique définit les algorithmes approuvés, longueurs de clés et usages (A.8.24)."},
            {"id": "tls",            "label": "Chiffrement en transit (TLS 1.2+ obligatoire)",             "desc": "Toutes les communications sensibles utilisent TLS 1.2 minimum. TLS 1.0/1.1 et SSL désactivés (A.8.24)."},
            {"id": "encryption_rest","label": "Chiffrement des données sensibles au repos",               "desc": "Les données sensibles stockées sont chiffrées (disques, bases de données, sauvegardes) (A.8.24)."},
            {"id": "key_mgmt",       "label": "Gestion du cycle de vie des clés cryptographiques",        "desc": "Génération, stockage, rotation et destruction des clés sont documentés et sécurisés (A.8.24)."},
        ],
    },
    {
        "id": "operations",
        "label": "Sécurité opérationnelle",
        "icon": "computer",
        "items": [
            {"id": "patch_mgmt",     "label": "Gestion des correctifs (critique < 72h)",                  "desc": "Un processus formel garantit l'application rapide des correctifs critiques sur tous les systèmes (A.8.8)."},
            {"id": "malware",        "label": "Protection contre les malwares (EDR/antivirus)",            "desc": "Une solution de détection endpoint est déployée sur tous les postes et serveurs (A.8.7)."},
            {"id": "logging",        "label": "Journalisation et surveillance des événements",             "desc": "Les logs d'accès et d'administration sont collectés, horodatés et conservés minimum 12 mois (A.8.15)."},
            {"id": "vuln_mgmt",      "label": "Gestion des vulnérabilités techniques",                    "desc": "Des scans de vulnérabilités sont réalisés régulièrement avec suivi des corrections (A.8.8)."},
            {"id": "change_mgmt",    "label": "Gestion des changements documentée",                       "desc": "Tout changement sur les systèmes suit un processus formel avec tests, approbation et rollback (A.8.32)."},
        ],
    },
    {
        "id": "incidents",
        "label": "Gestion des incidents",
        "icon": "warning",
        "items": [
            {"id": "incident_proc",  "label": "Procédure de réponse aux incidents documentée",            "desc": "Un processus formel de détection, qualification, réponse et clôture des incidents est établi (A.5.26)."},
            {"id": "incident_log",   "label": "Registre des incidents et retours d'expérience",           "desc": "Tous les incidents sont enregistrés avec analyse de cause racine et actions correctives (A.5.27)."},
            {"id": "breach_notif",   "label": "Processus de notification RGPD/CNIL (72h)",                "desc": "La procédure de notification en cas de violation de données personnelles est documentée et testée (A.5.28)."},
        ],
    },
    {
        "id": "continuity",
        "label": "Continuité d'activité",
        "icon": "restore",
        "items": [
            {"id": "bcp",            "label": "Plan de continuité (PCA) documenté et testé",              "desc": "Un PCA est maintenu, testé annuellement et couvre les scénarios de sinistre majeur (A.5.29)."},
            {"id": "backups",        "label": "Sauvegardes testées, chiffrées et hors ligne",             "desc": "Les sauvegardes suivent la règle 3-2-1, sont chiffrées et leur restauration est testée régulièrement (A.8.13)."},
            {"id": "rto_rpo",        "label": "RTO / RPO définis et atteignables",                        "desc": "Les objectifs de reprise (délai et point de reprise) sont formalisés et vérifiés lors des tests (A.5.30)."},
        ],
    },
    {
        "id": "suppliers",
        "label": "Relations fournisseurs",
        "icon": "account_tree",
        "items": [
            {"id": "supplier_policy","label": "Politique de sécurité fournisseurs documentée",            "desc": "Les exigences de sécurité applicables aux fournisseurs sont formalisées et communiquées (A.5.19)."},
            {"id": "supplier_contracts","label": "Clauses de sécurité dans les contrats fournisseurs",    "desc": "Les contrats incluent confidentialité, exigences de sécurité, notification d'incidents et droit d'audit (A.5.20)."},
            {"id": "supplier_monitor","label": "Surveillance et revue des fournisseurs critiques",        "desc": "Les fournisseurs ayant accès aux SI font l'objet d'une revue annuelle de leurs pratiques de sécurité (A.5.22)."},
        ],
    },
    {
        "id": "people",
        "label": "Ressources humaines & Formation",
        "icon": "school",
        "items": [
            {"id": "screening",      "label": "Vérification des antécédents à l'embauche",                "desc": "Des vérifications d'antécédents proportionnées aux risques sont effectuées avant recrutement (A.6.1)."},
            {"id": "awareness",      "label": "Programme de sensibilisation sécurité annuel",             "desc": "Tous les collaborateurs suivent une formation annuelle de sensibilisation à la sécurité (A.6.3)."},
            {"id": "nda",            "label": "Accords de confidentialité (NDA) signés",                  "desc": "Tout accès à des informations sensibles est couvert par un accord de confidentialité (A.6.6)."},
            {"id": "offboarding",    "label": "Procédure de départ sécurisée (offboarding)",              "desc": "La révocation des accès, restitution du matériel et rappel des obligations sont formalisés (A.6.5)."},
        ],
    },
]

# Pre-compute flat item list for validation
ALL_ITEM_IDS = {item["id"] for cat in ISO27001_CATEGORIES for item in cat["items"]}


def _compute_score(items: dict[str, str]) -> int:
    """Compute 0-100 score against all ISO 27001 items.
    compliant=2pts, partial=1pt, non_compliant=0, na excluded from denominator."""
    all_statuses = [items.get(id, "non_compliant") for id in ALL_ITEM_IDS]
    scorable = [s for s in all_statuses if s != "na"]
    if not scorable:
        return 0
    total = sum(2 if s == "compliant" else 1 if s == "partial" else 0 for s in scorable)
    max_pts = len(scorable) * 2
    return round(total / max_pts * 100) if max_pts else 0


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class Iso27001SaveIn(BaseModel):
    items: dict[str, str]


class Iso27001Out(BaseModel):
    items: dict[str, str]
    score: int
    updated_at: datetime | None
    categories: list

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/me", response_model=Iso27001Out)
async def get_assessment(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Iso27001Assessment).where(Iso27001Assessment.user_id == current_user.id)
    )
    assessment = result.scalar_one_or_none()
    items = json.loads(assessment.items_json) if assessment else {}
    score = assessment.score if assessment else 0
    updated_at = assessment.updated_at if assessment else None
    return {"items": items, "score": score, "updated_at": updated_at, "categories": ISO27001_CATEGORIES}


@router.put("/me", response_model=Iso27001Out)
async def save_assessment(
    payload: Iso27001SaveIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    for item_id, status in payload.items.items():
        if item_id not in ALL_ITEM_IDS:
            raise HTTPException(status_code=422, detail=f"Identifiant inconnu : {item_id}")
        if status not in VALID_STATUSES:
            raise HTTPException(status_code=422, detail=f"Statut invalide : {status}")

    score = _compute_score(payload.items)
    now = datetime.now(timezone.utc)

    result = await db.execute(
        select(Iso27001Assessment).where(Iso27001Assessment.user_id == current_user.id)
    )
    assessment = result.scalar_one_or_none()

    if assessment:
        assessment.items_json = json.dumps(payload.items)
        assessment.score = score
        assessment.updated_at = now
    else:
        assessment = Iso27001Assessment(
            user_id=current_user.id,
            items_json=json.dumps(payload.items),
            score=score,
            created_at=now,
            updated_at=now,
        )
        db.add(assessment)

    await db.commit()
    await db.refresh(assessment)
    return {"items": payload.items, "score": score, "updated_at": assessment.updated_at, "categories": ISO27001_CATEGORIES}


@router.get("/me/pdf")
async def export_assessment_pdf(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate an ISO 27001 compliance report PDF."""
    result = await db.execute(
        select(Iso27001Assessment).where(Iso27001Assessment.user_id == current_user.id)
    )
    assessment = result.scalar_one_or_none()
    items = json.loads(assessment.items_json) if assessment else {}
    score = _compute_score(items)
    updated_at = assessment.updated_at if assessment else None

    from app.services.iso27001_pdf import generate_iso27001_pdf
    pdf_bytes = generate_iso27001_pdf(
        categories=ISO27001_CATEGORIES,
        items=items,
        score=score,
        updated_at=updated_at,
        user_email=current_user.email,
    )

    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="cyberscan_iso27001_conformite.pdf"'},
    )
