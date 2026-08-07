"""Dossier de conformite NIS2 d'un client suivi — etape 5d.

CE QUE CE MODULE AJOUTE. L'etape 5b a rendu possible qu'un consultant detienne
une evaluation par client (`client_id` sur `nis2_assessments`). L'etape 5c a pose
les regles, la 5e la surface pour l'abonne direct, la 5f l'export. Il ne manquait
que le chemin cote consultant : c'est ici.

LE SUJET EST LE CLIENT, LE PROPRIETAIRE RESTE LE CONSULTANT. `user_id` designe
qui detient le dossier, `client_id` de qui il parle. Un consultant qui suit dix
clients detient dix dossiers en plus du sien.

LE DEPOT EST RESERVE AUX PLANS PAYANTS, ICI COMME COTE ABONNE DIRECT. Le role
consultant n'implique AUCUN abonnement : `is_rssi_consultant` est un booleen a
false par defaut, pose par un admin, sans le moindre lien avec un plan. Un compte
peut donc etre consultant et au Gratuit. La garde s'applique donc des deux cotes,
sans exception.

CE QUI RESTE OUVERT, ET C'EST LA MEME REGLE QU'AILLEURS : retirer une piece et la
telecharger ne sont pas gardes. Un consultant dont l'abonnement a lapse doit
pouvoir recuperer et nettoyer les dossiers de ses clients. L'export du document
auditeur non plus : c'est son livrable, et le bloquer sur son abonnement
personnel le priverait de rendre le travail deja fait.

CE QUE CETTE GARDE NE BORNE PAS. La creation de clients RSSI n'est plafonnee par
rien, et chaque client ouvre un quota de 500 Mo. Le cout reste donc fonction du
nombre de clients, pas du plan. C'est un constat, pas un oubli : aux montants en
jeu — de l'ordre du centime par mois et par client rempli — un plafond mal place
generait un consultant legitime pour rien.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_rssi_consultant, require_conformity_pieces
from app.models.user import User
from app.services import depot_service, nis2_service, preuve_service
from app.services.assessment_service import compute_assessment_score
from app.services.nis2_catalogue import ALL_ITEM_IDS, NIS2_CATEGORIES, VALID_STATUSES

from ._shared import _get_client_or_404

router = APIRouter()


class PieceClientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nom: str
    taille_octets: int
    statut_analyse: str
    rattache_le: datetime


class DossierNis2Out(BaseModel):
    items: dict[str, str]
    score: int
    updated_at: datetime | None
    categories: list
    pieces: dict[str, list[PieceClientOut]] = {}


class DossierNis2In(BaseModel):
    items: dict[str, str]


async def _dossier(db: AsyncSession, user_id: int, client_id: int) -> dict:
    """Etat du dossier d'un client, forme commune au GET et au PUT.

    Les deux doivent rendre exactement la meme chose : sans cela, les pieces
    disparaitraient de l'ecran juste apres un enregistrement.
    """
    evaluation = await nis2_service.get_user_assessment(db, user_id, client_id)
    return {
        "items": json.loads(evaluation.items_json) if evaluation else {},
        "score": evaluation.score if evaluation else 0,
        "updated_at": evaluation.updated_at if evaluation else None,
        "categories": NIS2_CATEGORIES,
        "pieces": (
            await preuve_service.preuves_par_critere(db, evaluation.id) if evaluation else {}
        ),
    }


@router.get("/clients/{client_id}/nis2", response_model=DossierNis2Out)
async def lire_le_dossier(
    client_id: int,
    current_user: User = Depends(get_rssi_consultant),
    db: AsyncSession = Depends(get_db),
):
    """Dossier NIS2 du client suivi."""
    client = await _get_client_or_404(client_id, current_user.id, db)
    return await _dossier(db, current_user.id, client.id)


@router.put("/clients/{client_id}/nis2", response_model=DossierNis2Out)
async def enregistrer_le_dossier(
    client_id: int,
    payload: DossierNis2In,
    current_user: User = Depends(get_rssi_consultant),
    db: AsyncSession = Depends(get_db),
):
    """Enregistre les reponses du dossier de ce client."""
    client = await _get_client_or_404(client_id, current_user.id, db)

    for item_id, statut in payload.items.items():
        if item_id not in ALL_ITEM_IDS:
            raise HTTPException(status_code=422, detail=f"Identifiant inconnu : {item_id}")
        if statut not in VALID_STATUSES:
            raise HTTPException(status_code=422, detail=f"Statut invalide : {statut}")

    await nis2_service.upsert_assessment(
        db,
        current_user.id,
        items=payload.items,
        score=compute_assessment_score(payload.items, ALL_ITEM_IDS),
        now=datetime.now(UTC),
        client_id=client.id,
    )
    return await _dossier(db, current_user.id, client.id)


@router.post(
    "/clients/{client_id}/nis2/criteres/{item_id}/pieces",
    response_model=PieceClientOut,
    status_code=201,
    dependencies=[Depends(require_conformity_pieces)],
)
async def joindre_une_piece(
    client_id: int,
    item_id: str,
    fichier: UploadFile = File(...),
    current_user: User = Depends(get_rssi_consultant),
    db: AsyncSession = Depends(get_db),
):
    """Depose un document et le rattache a un critere du dossier de ce client.

    MEME ORDRE DE CONTROLES QUE PARTOUT : critere connu, lecture bornee,
    signature, quota — avant d'ecrire quoi que ce soit sur S3.

    LA GARDE D'ABONNEMENT S'APPLIQUE : etre consultant n'implique aucun plan.

    LE QUOTA EST CELUI DU CLIENT, pas celui du consultant. Ce document appartient
    au suivi de ce client ; l'imputer au consultant ferait que ses dix clients se
    disputeraient un seul plafond.
    """
    from app.services.storage import (
        MAX_UPLOAD_BYTES,
        FichierTropVolumineuxError,
        lire_borne,
        upload_file,
        validate_upload,
    )

    client = await _get_client_or_404(client_id, current_user.id, db)

    try:
        critere = preuve_service.valider_critere(item_id)
    except preuve_service.CritereInconnuError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    try:
        contenu = await lire_borne(fichier, MAX_UPLOAD_BYTES)
    except FichierTropVolumineuxError as exc:
        raise HTTPException(status_code=413, detail=str(exc))

    nom = Path(fichier.filename or "document").name
    try:
        validate_upload(filename=nom, content_type=fichier.content_type or "", content=contenu)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    try:
        await depot_service.verifier_quota(db, len(contenu), client_id=client.id)
    except depot_service.QuotaDepassementError as exc:
        raise HTTPException(status_code=413, detail=str(exc))

    now = datetime.now(UTC)
    evaluation = await nis2_service.get_user_assessment(db, current_user.id, client.id)
    if evaluation is None:
        evaluation = await nis2_service.upsert_assessment(
            db, current_user.id, items={}, score=0, now=now, client_id=client.id
        )

    cle = upload_file(contenu, nom, current_user.id, client.id)
    enregistre = await depot_service.enregistrer_depot(
        db,
        cle_stockage=cle,
        nom_original=nom,
        taille_octets=len(contenu),
        type_mime=fichier.content_type or "",
        depose_par_id=current_user.id,
        client_id=client.id,
    )
    preuve = await preuve_service.rattacher(
        db,
        assessment_id=evaluation.id,
        item_id=critere,
        fichier_id=enregistre.id,
        now=now,
    )

    return {
        "id": preuve.id,
        "nom": enregistre.nom_original,
        "taille_octets": enregistre.taille_octets,
        "statut_analyse": enregistre.statut_analyse,
        "rattache_le": preuve.rattache_le,
    }


@router.delete("/clients/{client_id}/nis2/pieces/{piece_id}", status_code=204)
async def retirer_une_piece(
    client_id: int,
    piece_id: int,
    current_user: User = Depends(get_rssi_consultant),
    db: AsyncSession = Depends(get_db),
):
    """Detache une piece du dossier de ce client.

    Le fichier n'est pas efface : il redevient non reference, et la purge des
    orphelins s'en chargera avec son delai de grace.
    """
    client = await _get_client_or_404(client_id, current_user.id, db)
    evaluation = await nis2_service.get_user_assessment(db, current_user.id, client.id)
    if evaluation is None:
        raise HTTPException(status_code=404, detail="Pièce non trouvée")

    if not await preuve_service.detacher(db, assessment_id=evaluation.id, preuve_id=piece_id):
        raise HTTPException(status_code=404, detail="Pièce non trouvée")


@router.get("/clients/{client_id}/nis2/pieces/{piece_id}/download")
async def telecharger_une_piece(
    client_id: int,
    piece_id: int,
    current_user: User = Depends(get_rssi_consultant),
    db: AsyncSession = Depends(get_db),
):
    """Lien de telechargement, sous reserve de l'analyse antivirus.

    La regle de delivrance vaut ici comme ailleurs : un document dont l'analyse
    n'est pas concluante n'est pas servi, meme au consultant qui l'a depose.
    """
    from app.services.storage import get_download_url

    client = await _get_client_or_404(client_id, current_user.id, db)
    evaluation = await nis2_service.get_user_assessment(db, current_user.id, client.id)
    if evaluation is None:
        raise HTTPException(status_code=404, detail="Pièce non trouvée")

    cle = await preuve_service.cle_de_la_piece(db, assessment_id=evaluation.id, preuve_id=piece_id)
    if cle is None:
        raise HTTPException(status_code=404, detail="Pièce non trouvée")

    if not await depot_service.est_telechargeable(db, cle):
        raise HTTPException(
            status_code=409,
            detail="Ce document est en cours de vérification. Il sera disponible sous peu.",
        )
    return {"url": get_download_url(cle)}


@router.get("/clients/{client_id}/nis2/pdf/auditor")
async def exporter_le_dossier(
    client_id: int,
    current_user: User = Depends(get_rssi_consultant),
    db: AsyncSession = Depends(get_db),
):
    """Document auditeur du client, pieces comprises.

    C'est le livrable que le consultant remet : sans les pieces, il ne
    transmettrait qu'un questionnaire rempli.

    L'ENTITE NOMMEE EST LE CLIENT, PAS LE CONSULTANT. Un document qui porterait
    le nom du cabinet en en-tete d'attestation designerait la mauvaise entite —
    c'est la conformite du client qui est decrite.
    """
    import asyncio

    from app.services.nis2_auditor_pdf import generate_nis2_auditor_pdf

    client = await _get_client_or_404(client_id, current_user.id, db)
    etat = await _dossier(db, current_user.id, client.id)

    pdf_bytes = await asyncio.to_thread(
        generate_nis2_auditor_pdf,
        categories=NIS2_CATEGORIES,
        items=etat["items"],
        score=etat["score"],
        user_email=client.email or current_user.email,
        updated_at=etat["updated_at"],
        company_name=client.name,
        pieces=etat["pieces"],
    )

    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="nis2_dossier_client.pdf"',
        },
    )
