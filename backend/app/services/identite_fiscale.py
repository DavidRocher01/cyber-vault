"""Identifiants fiscaux francais : SIREN et numero de TVA intracommunautaire.

POURQUOI CE MODULE EXISTE. A partir du 1er septembre 2027, une facture entre
professionnels devra identifier l'ACHETEUR par son SIREN. Ce n'est pas une
mention decorative : c'est la cle sur laquelle l'administration rapproche les
factures des deux parties.

ET C'EST UNE DONNEE, PAS DU CODE. On peut ecrire le format Factur-X en 2027 ;
on ne peut pas inventer retroactivement le SIREN d'un client facture en 2026.
Chaque facture professionnelle emise sans lui laisse un trou qu'il faudra
combler client par client, en esperant qu'ils repondent. D'ou la collecte des
maintenant, un an avant l'echeance.

CE QUE STRIPE DONNE, ET SOUS QUELLE FORME. Stripe collecte un numero de TVA
(`eu_vat`), pas un SIREN. Pour la France le format est `FR` + une cle de deux
caracteres + les NEUF CHIFFRES DU SIREN : le SIREN se lit donc directement a la
fin. Stripe verifie le format, pas la validite — la verification de la cle,
elle, se fait ici.
"""

from __future__ import annotations

import re

_SIREN = re.compile(r"^\d{9}$")
_TVA_FR = re.compile(r"^FR([0-9A-Z]{2})(\d{9})$")


def normaliser(valeur: str | None) -> str:
    """Retire espaces, points et tirets — les clients les saisissent librement."""
    if not valeur:
        return ""
    return re.sub(r"[\s.\-]", "", valeur).upper()


def luhn_valide(chiffres: str) -> bool:
    """Cle de Luhn, celle qui valide un SIREN.

    Un SIREN mal saisi passe tous les controles de longueur mais echoue ici.
    C'est le seul filtre qui distingue une faute de frappe d'un numero reel.
    """
    total = 0
    for position, caractere in enumerate(reversed(chiffres)):
        n = int(caractere)
        if position % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


def siren_valide(valeur: str | None) -> bool:
    """Neuf chiffres ET une cle de Luhn correcte."""
    v = normaliser(valeur)
    return bool(_SIREN.match(v)) and luhn_valide(v)


def siren_depuis_tva(numero_tva: str | None) -> str | None:
    """Extrait le SIREN d'un numero de TVA francais, ou `None`.

    La cle de deux caracteres est verifiee QUAND ELLE EST NUMERIQUE :
    `(12 + 3 * (SIREN % 97)) % 97`. Les numeros les plus anciens portent une cle
    alphabetique attribuee autrement — on ne peut pas la recalculer, on se
    contente alors du SIREN lui-meme. Refuser ces numeros ecarterait des
    entreprises parfaitement en regle.
    """
    v = normaliser(numero_tva)
    correspondance = _TVA_FR.match(v)
    if not correspondance:
        return None

    cle, siren = correspondance.groups()
    if not luhn_valide(siren):
        return None

    if cle.isdigit() and int(cle) != (12 + 3 * (int(siren) % 97)) % 97:
        return None

    return siren


def siren_depuis_identifiant(type_stripe: str | None, valeur: str | None) -> str | None:
    """Traduit un identifiant fiscal Stripe en SIREN, quand c'est possible.

    Un client etranger a un identifiant valide qui n'est PAS un SIREN : on
    renvoie `None` sans le rejeter. La facturation electronique francaise ne le
    concerne pas, et refuser sa saisie l'empecherait d'acheter.
    """
    if type_stripe != "eu_vat":
        return None
    return siren_depuis_tva(valeur)
