"""
NIS2 Compliance endpoints — save/load user assessment and export PDF.
"""

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, require_conformity_export, require_conformity_pieces
from app.models.user import User
from app.services import (
    awareness_nis2_report,
    brand_service,
    depot_service,
    nis2_service,
    preuve_service,
)
from app.services.assessment_service import compute_assessment_score
from app.services.nis2_catalogue import ALL_ITEM_IDS, NIS2_CATEGORIES, VALID_STATUSES

router = APIRouter(prefix="/nis2", tags=["nis2"])

# Le catalogue des criteres vit dans `app/services/nis2_catalogue.py`. Ce
# routeur n'en est qu'un consommateur parmi d'autres : les deux generateurs de
# PDF le lisent aussi, et le rattachement de preuves aux criteres le lira.


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class Nis2SaveIn(BaseModel):
    items: dict[str, str]  # { item_id: status }


class PieceOut(BaseModel):
    """Une piece justificative rattachee a un critere."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    nom: str
    taille_octets: int
    # L'interface doit pouvoir montrer « en cours d'analyse » plutot que de
    # proposer un lien de telechargement qui repondra 409.
    statut_analyse: str
    rattache_le: datetime


class Nis2Out(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: dict[str, str]
    score: int
    updated_at: datetime | None
    categories: list  # static definition returned for convenience
    # Mesures objectives detenues par la plateforme pour certains items.
    # Ne repond PAS a la place de l'utilisateur : une auto-evaluation remplie
    # automatiquement n'est plus une declaration et perd sa valeur devant un
    # auditeur. On fournit la mesure, il declare.
    preuves: dict = {}
    # DEUX CHOSES DIFFERENTES, ET LE NOM LES SEPARE. `preuves` ci-dessus, ce sont
    # les mesures que la plateforme detient deja. `pieces` ci-dessous, ce sont
    # les documents que l'utilisateur a lui-meme deposes, par critere. Les
    # confondre sous un seul nom reviendrait a laisser croire que la plateforme
    # a produit ce que l'utilisateur a fourni.
    pieces: dict[str, list[PieceOut]] = {}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


async def _mesures_de_la_plateforme(db: AsyncSession, user_id: int) -> dict:
    """Les mesures objectives que la plateforme detient deja.

    Extrait ici parce que le GET et le PUT doivent rendre exactement la meme
    chose : sans cela, les mesures disparaitraient de l'ecran juste apres un
    enregistrement.
    """
    mesures: dict = {}
    formation = await awareness_nis2_report.preuve_formation(db, user_id)
    if formation:
        mesures["awareness"] = formation
    return mesures


async def _pieces_deposees(db: AsyncSession, assessment) -> dict:
    """Les documents deposes par l'utilisateur, regroupes par critere."""
    if assessment is None:
        return {}
    return await preuve_service.preuves_par_critere(db, assessment.id)


@router.get("/me", response_model=Nis2Out)
async def get_assessment(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    assessment = await nis2_service.get_user_assessment(db, current_user.id)

    return {
        "items": json.loads(assessment.items_json) if assessment else {},
        "score": assessment.score if assessment else 0,
        "updated_at": assessment.updated_at if assessment else None,
        "categories": NIS2_CATEGORIES,
        "preuves": await _mesures_de_la_plateforme(db, current_user.id),
        "pieces": await _pieces_deposees(db, assessment),
    }


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
    now = datetime.now(UTC)

    assessment = await nis2_service.upsert_assessment(
        db, current_user.id, items=payload.items, score=score, now=now
    )

    return {
        "items": payload.items,
        "score": score,
        "updated_at": assessment.updated_at,
        "categories": NIS2_CATEGORIES,
        "preuves": await _mesures_de_la_plateforme(db, current_user.id),
        "pieces": await _pieces_deposees(db, assessment),
    }


# ---------------------------------------------------------------------------
# Pieces justificatives
# ---------------------------------------------------------------------------


@router.post(
    "/me/criteres/{item_id}/pieces",
    response_model=PieceOut,
    status_code=201,
    dependencies=[Depends(require_conformity_pieces)],
)
async def deposer_une_piece(
    item_id: str,
    fichier: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Depose un document et le rattache a un critere, en un seul appel.

    UN SEUL APPEL, COMME COTE PORTAIL. Deposer puis rattacher en deux temps
    fabrique une fenetre pendant laquelle le fichier n'est reference par rien.
    Ici l'objet, la ligne de registre et le rattachement naissent ensemble.

    L'ORDRE DES CONTROLES EST CELUI DU COUT CROISSANT : critere connu, lecture
    bornee, signature, quota — tout cela AVANT d'ecrire sur S3. Refuser apres
    stockage laisserait un objet en place tout en annoncant un refus.

    LE CRITERE EST VALIDE EN PREMIER parce que c'est le controle le moins cher,
    et parce qu'un identifiant errone produirait une piece invisible et
    imperissable : invisible faute d'apparaitre sous un critere connu,
    imperissable parce qu'elle servirait formellement de preuve et echapperait a
    la purge des orphelins.

    L'EVALUATION EST CREEE SI ELLE N'EXISTE PAS. Exiger d'avoir enregistre son
    auto-evaluation avant de joindre une piece imposerait un ordre que rien ne
    justifie. Une evaluation vide rend exactement ce que rendait son absence —
    items vides, score a zero — donc rien ne change a l'ecran.
    """
    from app.services.storage import (
        MAX_UPLOAD_BYTES,
        FichierTropVolumineuxError,
        lire_borne,
        upload_file,
        validate_upload,
    )

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
        validate_upload(
            filename=nom,
            content_type=fichier.content_type or "",
            content=contenu,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    try:
        await depot_service.verifier_quota(db, len(contenu), user_id=current_user.id)
    except depot_service.QuotaDepassementError as exc:
        raise HTTPException(status_code=413, detail=str(exc))

    now = datetime.now(UTC)
    assessment = await nis2_service.get_user_assessment(db, current_user.id)
    if assessment is None:
        assessment = await nis2_service.upsert_assessment(
            db, current_user.id, items={}, score=0, now=now
        )

    # `client_id` reste nul : ce depot n'appartient a aucun suivi RSSI. C'est ce
    # qui le fait compter sur le quota du compte, et non sur celui d'un client.
    cle = upload_file(contenu, nom, current_user.id, None)
    enregistre = await depot_service.enregistrer_depot(
        db,
        cle_stockage=cle,
        nom_original=nom,
        taille_octets=len(contenu),
        type_mime=fichier.content_type or "",
        depose_par_id=current_user.id,
        client_id=None,
    )
    preuve = await preuve_service.rattacher(
        db,
        assessment_id=assessment.id,
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


@router.get("/me/pieces", response_model=dict[str, list[PieceOut]])
async def lister_les_pieces(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Les pieces et leur etat d'analyse, SANS le catalogue.

    POURQUOI UNE ROUTE A PART. `GET {base}` embarque les 34 criteres — une
    quinzaine de kilo-octets qui ne changent jamais. L'ecran interroge cette
    route toutes les dix secondes tant qu'une analyse antivirus est en cours :
    lui renvoyer le catalogue a chaque fois serait le retelecharger pour rien.

    Elle ne fait pas de travail supplementaire : elle rend exactement ce que
    `{base}` place deja dans son champ `pieces`.
    """
    assessment = await nis2_service.get_user_assessment(db, current_user.id)
    return await _pieces_deposees(db, assessment)


@router.delete("/me/pieces/{piece_id}", status_code=204)
async def retirer_une_piece(
    piece_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Detache une piece de son critere.

    PAS DE GARDE D'ABONNEMENT ICI, ET C'EST DELIBERE. Un abonne qui repasse au
    Gratuit doit pouvoir retirer ce qu'il a depose. Mettre le menage derriere un
    peage retiendrait ses documents en otage.

    Le fichier n'est pas efface : il redevient non reference, et la purge des
    orphelins s'en chargera avec son delai de grace habituel.
    """
    assessment = await nis2_service.get_user_assessment(db, current_user.id)
    if assessment is None:
        raise HTTPException(status_code=404, detail="Pièce non trouvée")

    if not await preuve_service.detacher(db, assessment_id=assessment.id, preuve_id=piece_id):
        raise HTTPException(status_code=404, detail="Pièce non trouvée")


@router.get("/me/pieces/{piece_id}/download")
async def telecharger_une_piece(
    piece_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lien de telechargement d'une piece, sous reserve de l'analyse antivirus.

    PAS DE GARDE D'ABONNEMENT NON PLUS : recuperer ses propres documents ne se
    monnaye pas.

    LA REGLE DE DELIVRANCE S'APPLIQUE SANS RIEN DE SPECIFIQUE. La piece est au
    registre commun, donc `est_telechargeable` la couvre deja : un fichier dont
    l'analyse n'est pas concluante n'est pas servi, meme a celui qui l'a depose.
    """
    from app.services.storage import get_download_url

    assessment = await nis2_service.get_user_assessment(db, current_user.id)
    if assessment is None:
        raise HTTPException(status_code=404, detail="Pièce non trouvée")

    cle = await preuve_service.cle_de_la_piece(db, assessment_id=assessment.id, preuve_id=piece_id)
    if cle is None:
        raise HTTPException(status_code=404, detail="Pièce non trouvée")

    if not await depot_service.est_telechargeable(db, cle):
        raise HTTPException(
            status_code=409,
            detail="Ce document est en cours de vérification. Il sera disponible sous peu.",
        )
    return {"url": get_download_url(cle)}


@router.get("/me/pdf", dependencies=[Depends(require_conformity_export)])
async def export_assessment_pdf(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a NIS2 compliance report PDF."""
    assessment = await nis2_service.get_user_assessment(db, current_user.id)
    items = json.loads(assessment.items_json) if assessment else {}
    score = compute_assessment_score(
        items, ALL_ITEM_IDS
    )  # recalcul avec la formule corrigée (34 items)
    updated_at = assessment.updated_at if assessment else None

    from app.services.nis2_pdf import generate_nis2_pdf

    pdf_bytes = await asyncio.to_thread(
        generate_nis2_pdf,
        categories=NIS2_CATEGORIES,
        items=items,
        score=score,
        updated_at=updated_at,
        user_email=current_user.email,
    )

    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="rochercybersecurite_nis2_conformite.pdf"'
        },
    )


@router.get("/me/pdf/auditor", dependencies=[Depends(require_conformity_export)])
async def export_auditor_pdf(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a formal NIS2 'prêt-à-déposer' document for certified auditor review.

    DEPUIS L'ETAPE 5f, IL EMBARQUE LES PIECES JUSTIFICATIVES. C'est ce qui fait
    la difference entre un questionnaire rempli et un dossier opposable :
    l'auditeur voit quel document appuie quel controle, et non seulement la
    reponse declaree.
    """
    assessment = await nis2_service.get_user_assessment(db, current_user.id)
    items = json.loads(assessment.items_json) if assessment else {}
    score = compute_assessment_score(items, ALL_ITEM_IDS)
    updated_at = assessment.updated_at if assessment else None
    pieces = await _pieces_deposees(db, assessment)

    # Try to get company name from brand profile
    brand = await brand_service.get_brand_profile(db, current_user.id)
    company_name = brand.company_name if brand else ""

    from app.services.nis2_auditor_pdf import generate_nis2_auditor_pdf

    pdf_bytes = await asyncio.to_thread(
        generate_nis2_auditor_pdf,
        categories=NIS2_CATEGORIES,
        items=items,
        score=score,
        user_email=current_user.email,
        updated_at=updated_at,
        company_name=company_name,
        pieces=pieces,
    )

    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="rochercybersecurite_nis2_pret_a_deposer.pdf"'
        },
    )
