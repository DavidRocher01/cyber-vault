"""Module sensibilisation employés — 5 mini-modules + progress tracking."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.training_progress import TrainingProgress
from app.models.user import User

router = APIRouter(prefix="/training", tags=["training"])

# ── Static module catalogue ────────────────────────────────────────────────────

MODULES: list[dict] = [
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
            {
                "id": "b",
                "text": "Je supprime l'email et contacte ma banque via son site officiel.",
            },
            {
                "id": "c",
                "text": "Je transfère l'email à mes collègues pour les prévenir.",
            },
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
            {
                "id": "a",
                "text": "Je me connecte au premier réseau disponible, le plus puissant.",
            },
            {
                "id": "b",
                "text": "Je demande au personnel le nom exact du réseau officiel, j'utilise un VPN.",
            },
            {
                "id": "c",
                "text": "Je reste sur le Wi-Fi public mais n'accède qu'aux emails.",
            },
            {
                "id": "d",
                "text": "Je désactive le Wi-Fi et utilise ma connexion 4G/5G mobile.",
            },
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
            {
                "id": "a",
                "text": "Je la branche pour voir qui elle appartient et la rendre.",
            },
            {
                "id": "b",
                "text": "Je la branche sur un ordinateur personnel, pas professionnel.",
            },
            {
                "id": "c",
                "text": "Je la remets à la sécurité ou à la DSI sans la brancher.",
            },
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
            {
                "id": "b",
                "text": "Je donne le code seulement s'ils connaissent mon nom.",
            },
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

MODULE_IDS = {m["id"] for m in MODULES}


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


@router.get("/modules", response_model=list[ModuleOut])
async def get_modules(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TrainingProgress).where(TrainingProgress.user_id == current_user.id)
    )
    done = {p.module_id: p.completed_at for p in result.scalars().all()}

    return [
        ModuleOut(
            **{k: v for k, v in m.items() if k != "choices"},
            choices=m["choices"],
            completed=m["id"] in done,
            completed_at=done.get(m["id"]),
        )
        for m in MODULES
    ]


@router.post("/modules/{module_id}/complete")
async def complete_module(
    module_id: str,
    payload: CompleteModuleIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if module_id not in MODULE_IDS:
        raise HTTPException(status_code=404, detail="Module introuvable")

    module = next(m for m in MODULES if m["id"] == module_id)
    correct = payload.answer == module["correct"]

    if correct:
        existing = await db.execute(
            select(TrainingProgress).where(
                TrainingProgress.user_id == current_user.id,
                TrainingProgress.module_id == module_id,
            )
        )
        if not existing.scalar_one_or_none():
            db.add(TrainingProgress(user_id=current_user.id, module_id=module_id))
            await db.commit()

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
    result = await db.execute(
        select(TrainingProgress).where(TrainingProgress.user_id == current_user.id)
    )
    done = result.scalars().all()
    total = len(MODULES)
    completed = len(done)
    return ProgressOut(
        completed=completed,
        total=total,
        percentage=round(completed / total * 100) if total > 0 else 0,
        completed_ids=[p.module_id for p in done],
    )
