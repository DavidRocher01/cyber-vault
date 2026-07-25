"""Module sensibilisation employés — modules training + awareness NIS2."""

from datetime import datetime

import yaml
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.awareness_module import AwarenessModule
from app.models.user import User
from app.services import training_service

router = APIRouter(prefix="/training", tags=["training"])

# ── Modules historiques (5 modules training originaux) ─────────────────────────

LEGACY_MODULES: list[dict] = [
    {
        "id": "phishing",
        "title": "Reconnaître le phishing",
        "icon": "phishing",
        "color": "red",
        "duration_min": 5,
        "description": "Apprenez à identifier les emails frauduleux et les tentatives d'hameçonnage.",
        "scenario": (
            'Vous recevez cet email : "Cher client, votre compte bancaire a été suspendu. '
            'Cliquez ici pour le réactiver immédiatement : http://secure-bank-verify.ru/login". '
            "Que faites-vous ?"
        ),
        "choices": [
            {"id": "a", "text": "Je clique sur le lien pour vérifier mon compte."},
            {"id": "b", "text": "Je supprime l'email et contacte ma banque via son site officiel."},
            {"id": "c", "text": "Je transfère l'email à mes collègues pour les prévenir."},
            {"id": "d", "text": "Je réponds à l'email pour signaler l'erreur."},
        ],
        "correct": "b",
        "explanation": (
            "Les banques ne demandent jamais de cliquer sur des liens par email pour vérifier votre compte. "
            "Le domaine '.ru' est un signal d'alarme. Toujours contacter votre banque via son site officiel "
            "ou en appelant le numéro au dos de votre carte."
        ),
    },
    {
        "id": "passwords",
        "title": "Mots de passe robustes",
        "icon": "key",
        "color": "blue",
        "duration_min": 4,
        "description": "Créez et gérez des mots de passe solides pour protéger vos comptes.",
        "scenario": (
            "Vous devez créer un nouveau mot de passe pour votre compte professionnel. "
            "Lequel de ces mots de passe est le plus sécurisé ?"
        ),
        "choices": [
            {"id": "a", "text": "motdepasse123"},
            {"id": "b", "text": "Jean1985!"},
            {"id": "c", "text": "Tr0ub4dor&3"},
            {"id": "d", "text": "aZ$9#mK!vL2@wQ8p"},
        ],
        "correct": "d",
        "explanation": (
            "Un mot de passe robuste contient au moins 12 caractères avec un mélange de majuscules, "
            "minuscules, chiffres et symboles. Évitez les mots du dictionnaire, les dates de naissance "
            "et les suites prévisibles. Utilisez un gestionnaire de mots de passe pour en générer "
            "et en retenir de complexes."
        ),
    },
    {
        "id": "wifi_public",
        "title": "Wi-Fi public — risques",
        "icon": "wifi",
        "color": "yellow",
        "duration_min": 4,
        "description": "Comprenez les dangers des réseaux Wi-Fi publics et comment vous protéger.",
        "scenario": (
            "Vous êtes dans un café et devez consulter vos emails professionnels. "
            "Vous voyez deux réseaux : 'Cafe_FREE_WiFi' et 'Cafe_Official_5G'. "
            "Que faites-vous ?"
        ),
        "choices": [
            {"id": "a", "text": "Je me connecte au premier réseau disponible, le plus puissant."},
            {
                "id": "b",
                "text": "Je demande au personnel le nom exact du réseau officiel, j'utilise un VPN.",
            },
            {"id": "c", "text": "Je reste sur le Wi-Fi public mais n'accède qu'aux emails."},
            {"id": "d", "text": "Je désactive le Wi-Fi et utilise ma connexion 4G/5G mobile."},
        ],
        "correct": "b",
        "explanation": (
            "Les deux réponses B et D sont bonnes. Sur un Wi-Fi public, des attaquants peuvent créer "
            "de faux points d'accès (evil twin). Toujours vérifier le nom exact du réseau auprès du personnel. "
            "Un VPN chiffre vos communications. La 4G/5G de votre opérateur est généralement plus sûre "
            "que n'importe quel Wi-Fi public."
        ),
    },
    {
        "id": "usb_unknown",
        "title": "Clés USB inconnues",
        "icon": "usb",
        "color": "orange",
        "duration_min": 3,
        "description": "Découvrez pourquoi brancher une clé USB inconnue peut compromettre votre système.",
        "scenario": (
            "Vous trouvez une clé USB dans le parking de votre entreprise avec une étiquette 'CONFIDENTIEL — RH'. "
            "Que faites-vous ?"
        ),
        "choices": [
            {"id": "a", "text": "Je la branche pour voir qui elle appartient et la rendre."},
            {"id": "b", "text": "Je la branche sur un ordinateur personnel, pas professionnel."},
            {"id": "c", "text": "Je la remets à la sécurité ou à la DSI sans la brancher."},
            {
                "id": "d",
                "text": "Je la garde sans la brancher jusqu'à ce que quelqu'un la réclame.",
            },
        ],
        "correct": "c",
        "explanation": (
            "C'est une technique d'attaque classique appelée 'USB drop'. Les attaquants déposent "
            "délibérément des clés USB piégées. Un seul branchement suffit pour installer un malware. "
            "Remettez toujours les clés USB inconnues à votre équipe de sécurité ou DSI sans les brancher."
        ),
    },
    {
        "id": "mfa",
        "title": "Double authentification (MFA)",
        "icon": "phonelink_lock",
        "color": "green",
        "duration_min": 4,
        "description": "Comprenez pourquoi le MFA est essentiel pour protéger vos comptes.",
        "scenario": (
            "Vous recevez un SMS avec un code 2FA que vous n'avez pas demandé, suivi d'un appel "
            "d'une personne prétendant être du support technique et demandant ce code. Que faites-vous ?"
        ),
        "choices": [
            {"id": "a", "text": "Je donne le code car la personne semble officielle."},
            {"id": "b", "text": "Je donne le code seulement s'ils connaissent mon nom."},
            {
                "id": "c",
                "text": "Je raccroche et contacte le vrai support via les canaux officiels.",
            },
            {"id": "d", "text": "Je demande à rappeler sur leur numéro."},
        ],
        "correct": "c",
        "explanation": (
            "Un code MFA ne doit jamais être communiqué à quelqu'un, même s'il prétend être du support. "
            "Si vous recevez un code non sollicité, cela signifie que quelqu'un essaie de se connecter "
            "à votre compte avec votre mot de passe. Changez immédiatement votre mot de passe et contactez "
            "le support via les canaux officiels."
        ),
    },
]

# IDs des modules legacy — on n'ajoutera pas les slugs awareness qui correspondent
# Alias pour compatibilité avec les tests existants
MODULES = LEGACY_MODULES

_LEGACY_IDS = {m["id"] for m in LEGACY_MODULES}

# Slugs awareness déjà couverts par les modules legacy
_AWARENESS_EXCLUDED_SLUGS = {"phishing-bases", "mots-de-passe", "mfa", "wifi-public", "usb-inconnu"}

# Mapping slug awareness → icône Material + couleur Tailwind
_SLUG_META: dict[str, tuple[str, str]] = {
    "ransomware": ("bug_report", "red"),
    "ingenerie-sociale": ("psychology", "purple"),
    "fraude-president": ("account_balance", "red"),
    "sauvegardes-321": ("backup", "blue"),
    "mobile-pro": ("smartphone", "green"),
    "rgpd-essentiel": ("gavel", "blue"),
    "ia-phishing": ("smart_toy", "orange"),
    "shadow-it": ("cloud_off", "yellow"),
    "teletravail-securite": ("home_work", "cyan"),
    "reseaux-sociaux-osint": ("share", "purple"),
    "signal-avant-cliquer": ("touch_app", "orange"),
    "apres-incident": ("healing", "green"),
    "chaine-approvisionnement": ("link", "purple"),
    "declaration-incident-nis2": ("notification_important", "red"),
    "chiffrement-pratique": ("lock", "blue"),
    "securite-physique": ("security", "green"),
    "gestion-vulnerabilites": ("system_update", "orange"),
    "continuite-activite-nis2": ("restart_alt", "cyan"),
    "cas-hopital-cyberattaque": ("local_hospital", "red"),
    "cas-pme-ransomware": ("business", "orange"),
    "cas-fraude-virement": ("payments", "red"),
    "dora-essentiel": ("account_balance", "purple"),
    "cra-essentiel": ("devices", "blue"),
}


def _awareness_module_to_training(mod: AwarenessModule) -> dict | None:
    """Convertit un AwarenessModule en dict compatible ModuleOut, en extrayant la 1ère question du quiz."""
    if not mod.quiz_yaml:
        return None
    try:
        quiz_data = yaml.safe_load(mod.quiz_yaml)
        questions = quiz_data.get("questions", [])
        if not questions:
            return None
        q = questions[0]
        answers = q.get("answers", [])
        if len(answers) < 2:
            return None

        choices = [{"id": a["id"], "text": a["text"]} for a in answers]
        correct_ids = [a["id"] for a in answers if a.get("correct")]
        correct = correct_ids[0] if correct_ids else answers[0]["id"]

        icon, color = _SLUG_META.get(mod.slug, ("school", "cyan"))

        return {
            "id": f"awareness_{mod.slug}",
            "title": mod.title,
            "icon": icon,
            "color": color,
            "duration_min": mod.estimated_duration_minutes or 5,
            "description": mod.description or "",
            "scenario": q.get("text", ""),
            "choices": choices,
            "correct": correct,
            "explanation": q.get("explanation", ""),
        }
    except (KeyError, TypeError, AttributeError):
        return None


# ── Schémas ────────────────────────────────────────────────────────────────────


class CompleteModuleIn(BaseModel):
    answer: str


class ModuleOut(BaseModel):
    id: str
    title: str
    icon: str
    color: str
    duration_min: int
    description: str
    scenario: str
    choices: list[dict]
    correct: str
    explanation: str
    completed: bool
    completed_at: datetime | None


class ProgressOut(BaseModel):
    completed: int
    total: int
    percentage: int
    completed_ids: list[str]


# ── Endpoints ──────────────────────────────────────────────────────────────────


async def _load_all_modules(db: AsyncSession) -> list[dict]:
    """Charge les modules legacy + les modules awareness (programme nis2-essentiel)."""
    modules: list[dict] = list(LEGACY_MODULES)

    mods = await training_service.load_program_modules(
        db, "nis2-essentiel", _AWARENESS_EXCLUDED_SLUGS
    )
    for mod in mods:
        converted = _awareness_module_to_training(mod)
        if converted:
            modules.append(converted)

    return modules


@router.get("/modules", response_model=list[ModuleOut])
async def get_modules(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    all_modules = await _load_all_modules(db)
    module_ids = {m["id"] for m in all_modules}

    done = {
        p.module_id: p.completed_at
        for p in await training_service.list_user_progress(db, current_user.id)
    }

    return [
        ModuleOut(
            **{k: v for k, v in m.items() if k != "choices"},
            choices=m["choices"],
            completed=m["id"] in done,
            completed_at=done.get(m["id"]),
        )
        for m in all_modules
        if m["id"] in module_ids
    ]


@router.post("/modules/{module_id}/complete")
async def complete_module(
    module_id: str,
    payload: CompleteModuleIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    all_modules = await _load_all_modules(db)
    module = next((m for m in all_modules if m["id"] == module_id), None)
    if not module:
        raise HTTPException(status_code=404, detail="Module introuvable")

    correct = payload.answer == module["correct"]

    if correct:
        await training_service.mark_module_complete(db, current_user.id, module_id)

    return {
        "correct": correct,
        "explanation": module["explanation"],
        "correct_answer": module["correct"],
    }


@router.get("/progress", response_model=ProgressOut)
async def get_progress(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    all_modules = await _load_all_modules(db)
    done = await training_service.list_user_progress(db, current_user.id)
    total = len(all_modules)
    completed = len(done)
    return ProgressOut(
        completed=completed,
        total=total,
        percentage=round(completed / total * 100) if total > 0 else 0,
        completed_ids=[p.module_id for p in done],
    )
