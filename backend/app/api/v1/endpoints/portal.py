"""Portail client RSSI — la mission d'un client, vue par lui.

Longtemps en LECTURE SEULE. Depuis l'étape 3 du dépôt de documents, le client
peut aussi **remettre** un document : politique de sécurité relue, preuve de
mise en œuvre, inventaire demandé lors d'une visite. C'est le besoin d'origine
du chantier, et il n'a pu être ouvert qu'une fois l'antivirus en service.

Toutes les routes dépendent de `get_current_rssi_client` : elles sont scopées au RssiClient
rattaché au compte connecté (client_user_id). Un client ne voit donc QUE ses propres données.
On n'expose volontairement pas les champs internes/CRM (consultant_user_id, pipedrive/pennylane/
notion, extra_data, file_url S3).
"""

from datetime import UTC, date, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_rssi_client
from app.models.rssi_action import RssiAction
from app.models.rssi_client import RssiClient
from app.services import portal_service

router = APIRouter(prefix="/portal", tags=["portal-client"])


# ── Schémas de sortie (champs sûrs uniquement) ────────────────────────────────


class ConsultantContact(BaseModel):
    display_name: str | None
    company_name: str | None
    email: str
    phone: str | None


class PortalActionOut(BaseModel):
    id: int
    title: str
    description: str | None
    category: str | None
    priority: str
    status: str
    assigned_to: str | None
    due_date: date | None
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class PortalVisitOut(BaseModel):
    id: int
    scheduled_date: date
    visit_type: str
    location: str | None
    status: str
    actual_date: date | None
    duration_hours: float | None

    model_config = {"from_attributes": True}


class PortalDeliverableOut(BaseModel):
    id: int
    title: str
    doc_type: str
    delivered_at: date
    notes: str | None
    has_file: bool
    # Le client doit distinguer ce qu'il a remis de ce qu'on lui a livré.
    origine: str
    # `en_analyse` / `sain` / `rejete` / `indetermine`. Exposé pour que
    # l'interface puisse expliquer une attente au lieu de la subir : un fichier
    # qui apparaît sans être téléchargeable ressemble sinon à une panne.
    statut_analyse: str | None


class PortalMeOut(BaseModel):
    name: str
    formula: str | None
    status: str
    contract_start_date: date | None
    contract_renewal_at: date | None
    consultant: ConsultantContact | None
    # Avancement de la mise en conformité (basé sur le plan d'action)
    progress_score: int
    actions_total: int
    actions_open: int
    actions_in_progress: int
    actions_done: int
    actions_overdue: int
    next_visit: PortalVisitOut | None


def _progress_score(actions: list[RssiAction]) -> int:
    """Score d'avancement 0-100 : done=2 pts, in_progress=1, open=0.
    Les actions annulées/reportées sont exclues du dénominateur."""
    considered = [a for a in actions if a.status in ("open", "in_progress", "done")]
    if not considered:
        return 0
    pts = sum(
        2 if a.status == "done" else 1 if a.status == "in_progress" else 0 for a in considered
    )
    return round(pts / (len(considered) * 2) * 100)


@router.get("/me", response_model=PortalMeOut)
async def get_my_mission(
    client: RssiClient = Depends(get_current_rssi_client),
    db: AsyncSession = Depends(get_db),
):
    actions = await portal_service.list_client_actions(db, client.id)
    today = datetime.now(UTC).date()
    overdue = sum(
        1
        for a in actions
        if a.status in ("open", "in_progress") and a.due_date and a.due_date < today
    )

    # Prochaine visite planifiée (à venir)
    next_visit = await portal_service.get_next_planned_visit(db, client.id, today)

    consultant = await portal_service.get_user(db, client.consultant_user_id)

    return PortalMeOut(
        name=client.name,
        formula=client.formula,
        status=client.status,
        contract_start_date=client.contract_start_date,
        contract_renewal_at=client.contract_renewal_at,
        consultant=ConsultantContact(
            display_name=consultant.display_name,
            company_name=consultant.company_name,
            email=consultant.email,
            phone=consultant.phone,
        )
        if consultant
        else None,
        progress_score=_progress_score(actions),
        actions_total=len(actions),
        actions_open=sum(1 for a in actions if a.status == "open"),
        actions_in_progress=sum(1 for a in actions if a.status == "in_progress"),
        actions_done=sum(1 for a in actions if a.status == "done"),
        actions_overdue=overdue,
        next_visit=PortalVisitOut.model_validate(next_visit) if next_visit else None,
    )


@router.get("/actions", response_model=list[PortalActionOut])
async def list_my_actions(
    client: RssiClient = Depends(get_current_rssi_client),
    db: AsyncSession = Depends(get_db),
):
    return await portal_service.list_client_actions(db, client.id)


@router.get("/visits", response_model=list[PortalVisitOut])
async def list_my_visits(
    client: RssiClient = Depends(get_current_rssi_client),
    db: AsyncSession = Depends(get_db),
):
    return await portal_service.list_client_visits(db, client.id)


@router.get("/deliverables", response_model=list[PortalDeliverableOut])
async def list_my_deliverables(
    client: RssiClient = Depends(get_current_rssi_client),
    db: AsyncSession = Depends(get_db),
):
    from app.services import depot_service

    deliverables = await portal_service.list_client_deliverables(db, client.id)
    sorties = []
    for d in deliverables:
        statut = None
        if d.file_url:
            fichier = await depot_service.fichier_par_cle(db, d.file_url)
            # `None` pour un fichier antérieur au registre : l'interface saura
            # qu'il n'y a pas d'attente à expliquer, plutôt que d'inventer un
            # état qu'on n'a pas.
            statut = fichier.statut_analyse if fichier else None
        sorties.append(
            PortalDeliverableOut(
                id=d.id,
                title=d.title,
                doc_type=d.doc_type,
                delivered_at=d.delivered_at,
                notes=d.notes,
                has_file=bool(d.file_url),
                origine=d.origine,
                statut_analyse=statut,
            )
        )
    return sorties


@router.post("/deliverables", response_model=PortalDeliverableOut, status_code=201)
async def deposer_un_document(
    fichier: UploadFile = File(...),
    titre: str = Form(...),
    client: RssiClient = Depends(get_current_rssi_client),
    db: AsyncSession = Depends(get_db),
):
    """Le client remet un document à son consultant.

    UN SEUL APPEL, ET C'EST DÉLIBÉRÉ. Le consultant dépose en deux temps —
    téléverser, récupérer une clé, créer le livrable — et c'est précisément cet
    intervalle qui fabrique les orphelins que la purge doit ensuite rattraper.
    Ici l'objet, le registre et le livrable naissent ensemble : pas de fenêtre.

    L'ORDRE DES CONTRÔLES EST CELUI DU COÛT CROISSANT. On lit de façon bornée,
    on valide la signature, on vérifie le quota — tout cela avant d'écrire quoi
    que ce soit sur S3. Refuser après stockage laisserait un objet en place tout
    en annonçant un refus.

    L'antivirus s'applique sans rien de spécifique : le fichier entre au
    registre avec l'état que `statut_a_l_enregistrement` décide, et la règle de
    délivrance vaut déjà pour cette route de téléchargement.
    """
    from app.models.enums import OrigineDepot
    from app.services import depot_service
    from app.services.storage import (
        MAX_UPLOAD_BYTES,
        FichierTropVolumineuxError,
        lire_borne,
        upload_file,
        validate_upload,
    )

    titre_propre = titre.strip()
    if not titre_propre:
        raise HTTPException(status_code=422, detail="Le titre du document est requis.")

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
        await depot_service.verifier_quota(db, client.id, len(contenu))
    except depot_service.QuotaDepassementError as exc:
        raise HTTPException(status_code=413, detail=str(exc))

    # `client.client_user_id` et non le consultant : le déposant est le client.
    cle = upload_file(contenu, nom, client.client_user_id, client.id)
    enregistre = await depot_service.enregistrer_depot(
        db,
        cle_stockage=cle,
        nom_original=nom,
        taille_octets=len(contenu),
        type_mime=fichier.content_type or "",
        depose_par_id=client.client_user_id,
        client_id=client.id,
    )
    livrable = await portal_service.creer_depot_client(
        db,
        client_id=client.id,
        titre=titre_propre,
        cle_stockage=cle,
        depose_le=datetime.now(UTC).date(),
    )
    return PortalDeliverableOut(
        id=livrable.id,
        title=livrable.title,
        doc_type=livrable.doc_type,
        delivered_at=livrable.delivered_at,
        notes=livrable.notes,
        has_file=True,
        origine=OrigineDepot.CLIENT,
        statut_analyse=enregistre.statut_analyse,
    )


@router.get("/deliverables/{deliverable_id}/download")
async def download_my_deliverable(
    deliverable_id: int,
    client: RssiClient = Depends(get_current_rssi_client),
    db: AsyncSession = Depends(get_db),
):
    from app.services import depot_service
    from app.services.storage import get_download_url

    deliverable = await portal_service.get_client_deliverable(db, deliverable_id, client.id)
    if deliverable is None:
        raise HTTPException(status_code=404, detail="Livrable non trouvé")
    if not deliverable.file_url:
        raise HTTPException(status_code=404, detail="Aucun fichier associé")

    # Meme regle que cote consultant, et c'est ici qu'elle compte le plus : le
    # client est celui qu'on protege quand la plateforme sert de vecteur.
    if not await depot_service.est_telechargeable(db, deliverable.file_url):
        raise HTTPException(
            status_code=409,
            detail="Ce document est en cours de vérification. Il sera disponible sous peu.",
        )
    return {"url": get_download_url(deliverable.file_url)}


@router.get("/report")
async def download_my_report(
    client: RssiClient = Depends(get_current_rssi_client),
    db: AsyncSession = Depends(get_db),
):
    """Rapport PDF de la mission (réutilise le générateur consultant)."""
    from app.services.rssi_report_pdf import generate_rssi_report

    actions = await portal_service.list_client_actions(db, client.id)
    visits = await portal_service.list_client_visits(db, client.id)
    deliverables = await portal_service.list_client_deliverables(db, client.id)
    consultant = await portal_service.get_user(db, client.consultant_user_id)

    client_dict = {
        "name": client.name,
        "email": client.email,
        "description": client.description,
        "formula": client.formula,
        "monthly_amount": float(client.monthly_amount) if client.monthly_amount else None,
        "contract_renewal_at": str(client.contract_renewal_at)
        if client.contract_renewal_at
        else None,
        "status": client.status,
    }
    actions_list = [
        {
            "title": a.title,
            "priority": a.priority,
            "status": a.status,
            "due_date": str(a.due_date) if a.due_date else None,
            "assigned_to": a.assigned_to,
            "category": a.category,
        }
        for a in actions
    ]
    visits_list = [
        {
            "scheduled_date": str(v.scheduled_date),
            "visit_type": v.visit_type,
            "location": v.location,
            "status": v.status,
            "duration_hours": float(v.duration_hours) if v.duration_hours else None,
            "actual_date": str(v.actual_date) if v.actual_date else None,
        }
        for v in visits
    ]
    deliverables_list = [
        {
            "title": d.title,
            "doc_type": d.doc_type,
            "delivered_at": str(d.delivered_at),
            "file_url": d.file_url,
            "notes": d.notes,
        }
        for d in deliverables
    ]
    consultant_dict = {
        "email": consultant.email if consultant else "",
        "display_name": consultant.display_name if consultant else None,
        "company_name": consultant.company_name if consultant else None,
        "phone": consultant.phone if consultant else None,
    }
    pdf_bytes = generate_rssi_report(
        client_dict, actions_list, visits_list, deliverables_list, consultant_dict
    )
    safe_name = client.name.replace(" ", "_").replace("/", "-").lower()
    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=rapport_rssi_{safe_name}.pdf"},
    )
