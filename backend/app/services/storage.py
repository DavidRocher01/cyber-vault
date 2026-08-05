"""File storage — S3 in prod, local filesystem fallback in dev."""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import UploadFile

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


def _s3_key(user_id: int, client_id: int, original_name: str) -> str:
    safe = Path(original_name).name.replace(" ", "_")
    return f"rssi-deliverables/{user_id}/{client_id}/{uuid.uuid4().hex}_{safe}"


def upload_file(content: bytes, original_name: str, user_id: int, client_id: int) -> str:
    """Upload a file and return its storage key."""
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


def _upload_s3(content: bytes, original_name: str, user_id: int, client_id: int) -> str:
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


def _upload_local(content: bytes, original_name: str, user_id: int, client_id: int) -> str:
    dest_dir = _LOCAL_UPLOAD_DIR / str(user_id) / str(client_id)
    dest_dir.mkdir(parents=True, exist_ok=True)
    safe = Path(original_name).name.replace(" ", "_")
    filename = f"{uuid.uuid4().hex}_{safe}"
    path = dest_dir / filename
    path.write_bytes(content)
    return str(Path("uploads") / "rssi" / str(user_id) / str(client_id) / filename).replace(
        "\\", "/"
    )
