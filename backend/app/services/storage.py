"""File storage — S3 in prod, local filesystem fallback in dev."""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import UploadFile
from loguru import logger

from app.core.config import settings

_LOCAL_UPLOAD_DIR = Path("uploads") / "rssi"
_ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.oasis.opendocument.text",
    "application/vnd.oasis.opendocument.spreadsheet",
    "image/png",
    "image/jpeg",
}
_ALLOWED_EXTENSIONS = {
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".odt",
    ".ods",
    ".png",
    ".jpg",
    ".jpeg",
}
MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20 MB

# Signatures de debut de fichier ("magic bytes"), par extension declaree.
#
# POURQUOI. L'extension et l'en-tete `Content-Type` viennent tous deux du
# client : la premiere est un bout de chaine, le second un en-tete multipart que
# n'importe quel outil pose a sa guise. Deux listes blanches comparees a des
# valeurs fournies par l'appelant ne contraignent donc rien. Les octets, eux,
# sont la seule chose qu'on tienne vraiment.
_ZIP = (b"PK\x03\x04",)  # OOXML et OpenDocument sont des archives ZIP
_OLE2 = (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1",)  # conteneur Word/Excel 97-2003

_SIGNATURES: dict[str, tuple[bytes, ...]] = {
    ".pdf": (b"%PDF-",),
    ".png": (b"\x89PNG\r\n\x1a\n",),
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
    ".docx": _ZIP,
    ".xlsx": _ZIP,
    ".odt": _ZIP,
    ".ods": _ZIP,
    ".doc": _OLE2,
    ".xls": _OLE2,
}


def _signature_coherente(contenu: bytes, extension: str) -> bool:
    """L'en-tete des octets correspond-il a l'extension annoncee ?

    Un fichier vide ou plus court que la signature attendue est refuse : on
    n'accepte pas ce qu'on ne peut pas verifier.

    CE QUE CE CONTROLE NE FAIT PAS. Pour les formats a base d'archive — docx,
    xlsx, odt, ods — il etablit qu'il s'agit d'un ZIP, pas que le ZIP contienne
    un document. Descendre plus bas voudrait dire ouvrir l'archive, donc parser
    une entree fournie par l'utilisateur : exactement la surface d'attaque que
    la conception (`docs/DEPOT_DOCUMENTS.md`) ecarte en commencant par des
    documents « lus » et non « traites ». C'est l'antivirus, etape suivante, qui
    couvre le contenu.
    """
    signatures = _SIGNATURES.get(extension)
    if signatures is None:  # extension hors liste blanche — deja refusee avant
        return False
    return any(contenu.startswith(s) for s in signatures)


class FichierTropVolumineuxError(ValueError):
    """Le corps envoyé dépasse le plafond autorisé pour ce point de dépôt."""

    def __init__(self, max_octets: int) -> None:
        self.max_octets = max_octets
        super().__init__(f"Fichier trop volumineux — maximum {max_octets // (1024 * 1024)} Mo")


async def lire_borne(fichier: UploadFile, max_octets: int) -> bytes:
    """Lit AU PLUS `max_octets + 1` octets, et refuse au-delà.

    L'ordre est tout : `await fichier.read()` puis `if len(...) > cap` charge
    d'abord l'intégralité en mémoire, et ne mesure qu'ensuite. Le plafond n'est
    alors qu'un message d'erreur, pas un rempart — la production tourne sur une
    seule tâche de 2 Go, et un abonné authentifie suffit a la faire tomber.

    Ce patron existait depuis la remediation S4 (finding #14) mais vivait en
    dur dans un seul endpoint : les trois autres points de depot ne l'avaient
    jamais recu. Il est ici pour que la bonne facon soit aussi la plus simple.

    Leve `FichierTropVolumineuxError` — aux endpoints de la traduire en 413,
    les services ne connaissant pas HTTP.
    """
    contenu = await fichier.read(max_octets + 1)
    if len(contenu) > max_octets:
        raise FichierTropVolumineuxError(max_octets)
    return contenu


def validate_upload(filename: str, content_type: str, content: bytes) -> None:
    """Refuse un dépôt invalide, avec un message destiné à l'utilisateur.

    Prend les OCTETS et non une taille déclarée : la taille s'en déduit, ce qui
    supprime tout écart entre ce que l'appelant annonce et ce qui sera stocké,
    et rend possible le contrôle de signature ci-dessous.

    Les trois contrôles ne se valent pas. L'extension et le `Content-Type`
    disent l'INTENTION du client — utiles pour un message clair, faciles à
    falsifier. La signature dit ce que le fichier EST. Le `Content-Type` reste
    volontairement souple : le durcir ferait rejeter des dépôts légitimes (les
    navigateurs envoient volontiers `application/octet-stream` pour un .docx)
    sans rien ajouter, puisque les octets tranchent désormais.

    Lève `ValueError`, aux endpoints de la traduire en 422.
    """
    ext = Path(filename).suffix.lower()
    if ext not in _ALLOWED_EXTENSIONS:
        raise ValueError(
            f"Extension non autorisée. Formats acceptés : {', '.join(sorted(_ALLOWED_EXTENSIONS))}"
        )
    if content_type not in _ALLOWED_MIME_TYPES:
        raise ValueError("Type de fichier non autorisé.")
    if len(content) > MAX_UPLOAD_BYTES:
        raise ValueError("Fichier trop volumineux (max 20 Mo).")
    if not _signature_coherente(content, ext):
        raise ValueError(
            f"Le contenu du fichier ne correspond pas à un {ext.lstrip('.').upper()}. "
            "Renommer un fichier ne change pas sa nature."
        )


# Segment de chemin des depots qui ne relevent d'aucun suivi RSSI : les pieces
# justificatives d'un abonne qui utilise la conformite seul. Sans lui, un
# `client_id` a None se serait ecrit « None » dans la cle, sous un prefixe
# `rssi-deliverables` qui aurait de surcroit menti sur la nature du fichier.
SEGMENT_HORS_SUIVI = "conformite"


def _segment_client(client_id: int | None) -> str:
    return SEGMENT_HORS_SUIVI if client_id is None else str(client_id)


def _s3_key(user_id: int, client_id: int | None, original_name: str) -> str:
    safe = Path(original_name).name.replace(" ", "_")
    return f"rssi-deliverables/{user_id}/{_segment_client(client_id)}/{uuid.uuid4().hex}_{safe}"


def upload_file(content: bytes, original_name: str, user_id: int, client_id: int | None) -> str:
    """Upload a file and return its storage key.

    `client_id` peut etre nul depuis l'etape 5e : une piece justificative
    deposee hors de tout suivi RSSI n'appartient a aucun client.
    """
    if settings.S3_BUCKET_NAME:
        return _upload_s3(content, original_name, user_id, client_id)
    return _upload_local(content, original_name, user_id, client_id)


def lire_balise(key: str, nom: str) -> str | None:
    """Rend la valeur d'une balise S3, ou `None` si absente.

    Sert à relire le verdict que GuardDuty pose sur l'objet après analyse. Rend
    `None` — et non une chaîne vide — quand la balise n'est pas là : l'appelant
    doit pouvoir distinguer « pas encore analysé » de « analysé sans verdict ».

    Sans bucket S3 configuré (développement, repli disque), il n'y a pas de
    balise : `None` est alors la réponse honnête, et l'antivirus est de toute
    façon inactif dans ce cas.
    """
    if not settings.S3_BUCKET_NAME:
        return None

    import boto3

    s3 = boto3.client("s3", region_name=settings.AWS_REGION)
    reponse = s3.get_object_tagging(Bucket=settings.S3_BUCKET_NAME, Key=key)
    for balise in reponse.get("TagSet", []):
        if balise.get("Key") == nom:
            return str(balise.get("Value", ""))
    return None


def supprimer_fichier(key: str) -> None:
    """Efface l'objet stocké sous `key`. Idempotent.

    Effacer un fichier déjà absent n'est PAS une erreur : la purge doit pouvoir
    rejouer sans se bloquer sur un objet qu'un passage précédent avait déjà
    supprimé, ou qu'un ménage manuel a retiré. S3 traite `delete_object` sur une
    clé inexistante comme un succès ; le repli disque fait de même avec
    `missing_ok`.

    Ne rattrape PAS les autres erreurs (droits, réseau) : l'appelant doit savoir
    que l'objet est toujours là, pour garder sa ligne de registre et réessayer.
    Perdre la trace d'un fichier qu'on n'a pas réussi à effacer, c'est le
    condamner à rester sur S3 sans que rien ne s'en souvienne.
    """
    if settings.S3_BUCKET_NAME and key.startswith("rssi-deliverables/"):
        import boto3

        s3 = boto3.client("s3", region_name=settings.AWS_REGION)
        s3.delete_object(Bucket=settings.S3_BUCKET_NAME, Key=key)
        return
    # Repli disque local. `Path(key).name` ne suffit pas ici : la clé porte le
    # chemin complet renvoyé par `_upload_local`. On refuse toutefois de sortir
    # du répertoire de dépôt, une clé venant de la base restant une donnée.
    chemin = Path(key)
    if chemin.is_absolute() or ".." in chemin.parts:
        raise ValueError(f"Clé de stockage refusée : {key!r}")
    chemin.unlink(missing_ok=True)


def get_download_url(key: str, expires: int = 3600) -> str:
    """Return a download URL for a stored key (presigned if S3, local path if local)."""
    if settings.S3_BUCKET_NAME and key.startswith("rssi-deliverables/"):
        return _presign_s3(key, expires)
    # Local: key is a relative path like "uploads/rssi/..."
    return f"/{key}"


# ── S3 backend ─────────────────────────────────────────────────────────────────


def _upload_s3(content: bytes, original_name: str, user_id: int, client_id: int | None) -> str:
    import boto3  # lazy import — only needed when S3 is configured

    key = _s3_key(user_id, client_id, original_name)
    s3 = boto3.client("s3", region_name=settings.AWS_REGION)
    s3.put_object(
        Bucket=settings.S3_BUCKET_NAME,
        Key=key,
        Body=content,
        ContentDisposition=f'attachment; filename="{Path(original_name).name}"',
    )
    return key


def _presign_s3(key: str, expires: int) -> str:
    import boto3

    s3 = boto3.client("s3", region_name=settings.AWS_REGION)
    return s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.S3_BUCKET_NAME, "Key": key},
        ExpiresIn=expires,
    )


# ── Local filesystem backend ───────────────────────────────────────────────────


def _upload_local(content: bytes, original_name: str, user_id: int, client_id: int | None) -> str:
    dest_dir = _LOCAL_UPLOAD_DIR / str(user_id) / _segment_client(client_id)
    dest_dir.mkdir(parents=True, exist_ok=True)
    safe = Path(original_name).name.replace(" ", "_")
    filename = f"{uuid.uuid4().hex}_{safe}"
    path = dest_dir / filename
    path.write_bytes(content)
    return str(
        Path("uploads") / "rssi" / str(user_id) / _segment_client(client_id) / filename
    ).replace("\\", "/")


# ── Rapports de scan ───────────────────────────────────────────────────────────
#
# POURQUOI CETTE SECTION EXISTE. Les rapports PDF etaient ecrits sur le disque du
# conteneur et leur CHEMIN ABSOLU stocke en base. Or le stockage d'une tache
# Fargate est EPHEMERE : chaque deploiement remplace la tache et emporte tous les
# rapports. La base continuait d'affirmer qu'ils existaient.
#
# Mesure du 2026-08-09, sept minutes apres un deploiement :
#
#     GET /api/v1/scans/163/pdf -> 500
#     RuntimeError: File at path /cyber-scanner/reports/clients/scan_163.pdf
#                   does not exist.
#
# On deploie plusieurs fois par jour. Sans clients, ca ne coute rien ; avec, tout
# client rouvrant son rapport de la veille recevrait une erreur serveur.
#
# LE MEME SEAU QUE LES DEPOTS, SOUS UN SOUS-PREFIXE DEDIE. Aucune infrastructure
# a creer, et la purge des depots ne peut pas les atteindre : elle travaille
# depuis les enregistrements de `fichiers_deposes`, jamais en enumerant le seau.
#
# LE PREFIXE COMMENCE PAR `rssi-deliverables/`, ET CE N'EST PAS COSMETIQUE. La
# politique IAM du role de tache n'autorise QUE :
#
#     arn:aws:s3:::cybervault-rssi-deliverables-prod/rssi-deliverables/*
#
# Un premier essai rangeait sous `rapports/` : chaque scan aurait echoue en
# production sur un AccessDenied, sans qu'aucun test ne puisse le voir — ils
# passent tous par le repli local. On se range dans le droit accorde plutot que
# de l'elargir.

_PREFIXE_RAPPORTS = "rssi-deliverables/rapports"
_LOCAL_RAPPORTS_DIR = Path("uploads") / "rapports"


def _est_un_chemin_local(reference: str) -> bool:
    """Une reference d'AVANT cette section : un chemin absolu de conteneur.

    Ces lignes existent encore en base. Elles pointent vers des fichiers presque
    surement disparus — on les lit quand meme, plutot que de les declarer
    perdues sans essayer.
    """
    return reference.startswith("/") or (len(reference) > 1 and reference[1] == ":")


def ranger_rapport(contenu: bytes, nom: str) -> str:
    """Range un rapport et retourne SA REFERENCE — jamais un chemin de disque.

    C'est la distinction qui compte : un chemin ne survit pas au conteneur qui
    l'a ecrit, une reference si.
    """
    if settings.S3_BUCKET_NAME:
        import boto3  # lazy import — seulement quand S3 est configure

        cle = f"{_PREFIXE_RAPPORTS}/{Path(nom).name}"
        boto3.client("s3", region_name=settings.AWS_REGION).put_object(
            Bucket=settings.S3_BUCKET_NAME,
            Key=cle,
            Body=contenu,
            ContentType="application/pdf",
            ContentDisposition=f'attachment; filename="{Path(nom).name}"',
        )
        return cle

    _LOCAL_RAPPORTS_DIR.mkdir(parents=True, exist_ok=True)
    chemin = _LOCAL_RAPPORTS_DIR / Path(nom).name
    chemin.write_bytes(contenu)
    return str(chemin).replace("\\", "/")


def lire_rapport(reference: str) -> bytes | None:
    """Contenu du rapport, ou `None` s'il a disparu.

    RENVOYER `None` PLUTOT QUE DE LAISSER JAILLIR L'EXCEPTION est tout l'objet de
    cette fonction : l'appelant peut alors repondre 404 avec une phrase utile,
    au lieu d'une erreur serveur qui reveille l'alarme et n'apprend rien a
    personne.
    """
    if _est_un_chemin_local(reference) or reference.startswith("uploads/"):
        chemin = Path(reference)
        return chemin.read_bytes() if chemin.is_file() else None

    if not settings.S3_BUCKET_NAME:
        return None

    import boto3
    from botocore.exceptions import ClientError

    try:
        objet = boto3.client("s3", region_name=settings.AWS_REGION).get_object(
            Bucket=settings.S3_BUCKET_NAME, Key=reference
        )
        return bytes(objet["Body"].read())
    except ClientError:
        # Objet absent, seau inaccessible : dans tous les cas, pas de rapport a
        # servir. On ne distingue pas — l'appelant n'en ferait rien.
        return None


def verifier_ecriture_stockage() -> None:
    """Verifie AU DEMARRAGE que le stockage configure est reellement ecrivable.

    POURQUOI, ET CE QUE CA A COUTE. Le 2026-08-10, un rangement de rapports a
    failli partir avec un prefixe hors du droit accorde au role de tache ECS :

        Autorise : cybervault-rssi-deliverables-prod/rssi-deliverables/*
        Ecrit    : rapports/*

    Chaque scan aurait echoue sur un AccessDenied — a la PREMIERE REQUETE D'UN
    UTILISATEUR, plusieurs heures apres la mise en production, et sous forme
    d'erreur 500. Aucun test ne pouvait le voir : ils passent tous par le repli
    disque, qui ne connait ni S3 ni IAM.

    UN REFUS DE DROIT N'EST JAMAIS PASSAGER : c'est toujours une erreur de
    configuration. On refuse donc de demarrer, ce qui fait echouer la bascule
    ECS et ramene la version precedente — exactement ce qu'on veut.

    UNE INDISPONIBILITE PASSAGERE, ELLE, NE DOIT PAS FAIRE TOMBER LE SERVICE.
    Reseau coupe, S3 lent, jeton en cours de renouvellement : on journalise et
    on demarre. Confondre les deux transformerait ce garde-fou en panne.
    """
    if not settings.S3_BUCKET_NAME:
        # Repli disque : rien a verifier, et surtout rien a exiger.
        return

    import boto3
    from botocore.exceptions import ClientError

    cle = f"{_PREFIXE_RAPPORTS}/.verification-demarrage"
    s3 = boto3.client("s3", region_name=settings.AWS_REGION)
    try:
        s3.put_object(Bucket=settings.S3_BUCKET_NAME, Key=cle, Body=b"ok")
        s3.delete_object(Bucket=settings.S3_BUCKET_NAME, Key=cle)
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        if code in {"AccessDenied", "AllAccessDisabled", "InvalidAccessKeyId", "NoSuchBucket"}:
            raise RuntimeError(
                f"Stockage inutilisable : {code} sur "
                f"s3://{settings.S3_BUCKET_NAME}/{cle}. "
                "Le role de tache n'a pas le droit d'ecrire sous ce prefixe — "
                "verifier la politique IAM et _PREFIXE_RAPPORTS."
            ) from exc

        # Tout le reste est traite comme passager.
        logger.warning(f"Verification du stockage impossible ({code}) — demarrage poursuivi.")
