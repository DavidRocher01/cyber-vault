"""Verification des signatures de webhook Svix — celles de Resend.

POURQUOI C'EST INDISPENSABLE. Ce webhook met des adresses en liste de
suppression. Sans verification, N'IMPORTE QUI connaissant l'URL pourrait faire
cesser tout envoi vers l'adresse de son choix — reinitialisation de mot de passe
comprise. Un endpoint qui accepte tout serait pire que pas d'endpoint du tout.

L'ALGORITHME, tel que documente par Svix :
  contenu signe = "{svix-id}.{svix-timestamp}.{corps brut}"
  cle           = base64decode(secret prive du prefixe `whsec_`)
  signature     = base64(HMAC-SHA256(cle, contenu signe))
  en-tete       = "v1,<sig> v1,<autre>" — plusieurs signatures possibles

LE CORPS DOIT ETRE LE CORPS BRUT. Reserialiser le JSON parse changerait un
espace ou un ordre de cle, et la signature ne correspondrait plus. C'est l'erreur
classique sur ce type de verification.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import time

# Fenetre de tolerance sur l'horodatage. Sans elle, une requete signee et
# interceptee reste rejouable indefiniment.
TOLERANCE_SECONDES = 5 * 60


def _cle(secret: str) -> bytes:
    brut = secret.removeprefix("whsec_")
    return base64.b64decode(brut)


def horodatage_acceptable(timestamp: str, maintenant: float | None = None) -> bool:
    try:
        envoi = int(timestamp)
    except (TypeError, ValueError):
        return False
    ecart = abs((maintenant if maintenant is not None else time.time()) - envoi)
    return ecart <= TOLERANCE_SECONDES


def signature_attendue(secret: str, svix_id: str, timestamp: str, corps: bytes) -> str:
    contenu = f"{svix_id}.{timestamp}.".encode() + corps
    empreinte = hmac.new(_cle(secret), contenu, hashlib.sha256).digest()
    return base64.b64encode(empreinte).decode()


def verifier(
    secret: str,
    svix_id: str | None,
    timestamp: str | None,
    signature_entete: str | None,
    corps: bytes,
    maintenant: float | None = None,
) -> bool:
    """Vrai si la requete est authentique et recente."""
    if not secret or not svix_id or not timestamp or not signature_entete:
        return False
    if not horodatage_acceptable(timestamp, maintenant):
        return False

    try:
        attendue = signature_attendue(secret, svix_id, timestamp, corps)
    except Exception:
        # Secret mal forme : on refuse, on ne laisse pas passer.
        return False

    for element in signature_entete.split(" "):
        version, _, valeur = element.partition(",")
        if version != "v1" or not valeur:
            continue
        # `compare_digest` et non `==` : une comparaison naive s'arrete au
        # premier caractere different, ce qui laisse mesurer la signature.
        if hmac.compare_digest(valeur, attendue):
            return True
    return False
