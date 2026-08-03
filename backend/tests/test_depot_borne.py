"""Tout point de depot lit de facon BORNEE.

Un `await file.read()` nu charge l'integralite du corps en memoire avant tout
controle. Verifier la taille ENSUITE ne protege de rien : la memoire est deja
consommee, et la production tourne sur une seule tache de 2 Go — un abonne
authentifie suffisait a la faire tomber.

Le patron correct existait depuis la remediation S4 (finding #14), mais vivait
en dur dans le seul endpoint Dark Web. Les trois autres ne l'avaient jamais
recu, dont `phishing` qui n'avait AUCUN plafond. Ces tests existent pour que ca
ne se reproduise pas.
"""

import inspect
import pathlib
import re

import pytest
from fastapi import UploadFile

from app.services.storage import FichierTropVolumineuxError, lire_borne

ENDPOINTS = pathlib.Path(__file__).resolve().parents[1] / "app" / "api" / "v1" / "endpoints"


class _FauxFichier:
    """Rend `taille_disponible` octets, quel que soit le plafond demande.

    On ne fabrique PAS un corps geant en memoire : ce serait reproduire le
    defaut qu'on teste. On verifie que l'appelant borne sa demande.
    """

    def __init__(self, taille_disponible: int) -> None:
        self.taille_disponible = taille_disponible
        self.demande: int | None = None

    async def read(self, taille: int = -1) -> bytes:
        self.demande = taille
        if taille < 0:
            return b"x" * self.taille_disponible
        return b"x" * min(taille, self.taille_disponible)


class TestLireBorne:
    @pytest.mark.asyncio
    async def test_ne_demande_jamais_plus_que_le_plafond(self):
        """Le point essentiel : la borne est passee a `read`, pas verifiee apres."""
        fichier = _FauxFichier(taille_disponible=10)
        await lire_borne(fichier, 1024)
        assert fichier.demande == 1025, "read() doit etre borne a max+1, jamais illimite"

    @pytest.mark.asyncio
    async def test_refuse_au_dela_du_plafond(self):
        fichier = _FauxFichier(taille_disponible=5000)
        with pytest.raises(FichierTropVolumineuxError):
            await lire_borne(fichier, 1024)

    @pytest.mark.asyncio
    async def test_accepte_pile_le_plafond(self):
        """Un fichier exactement a la limite doit passer : le +1 sert a detecter
        le depassement, pas a rogner un octet."""
        fichier = _FauxFichier(taille_disponible=1024)
        assert len(await lire_borne(fichier, 1024)) == 1024

    @pytest.mark.asyncio
    async def test_le_message_annonce_la_limite_en_mo(self):
        fichier = _FauxFichier(taille_disponible=5 * 1024 * 1024)
        with pytest.raises(FichierTropVolumineuxError, match="2 Mo"):
            await lire_borne(fichier, 2 * 1024 * 1024)

    def test_accepte_un_vrai_upload_file(self):
        """La signature doit correspondre au type reellement passe par FastAPI."""
        annotation = inspect.signature(lire_borne).parameters["fichier"].annotation
        assert annotation in (UploadFile, "UploadFile")


def test_aucun_endpoint_ne_lit_sans_borne():
    """Garde-fou structurel — celui qui manquait.

    Le defaut n'etait pas qu'un developpeur ait mal ecrit un endpoint : c'est
    que la bonne facon n'etait ecrite nulle part de partageable. Ce test refuse
    tout `read()` sans argument sur un fichier envoye.
    """
    coupables = []
    # `.read()` sans argument, sur un objet dont le nom evoque un fichier envoye.
    motif = re.compile(r"await\s+(\w*(?:file|csv|upload|fichier)\w*)\.read\(\s*\)", re.I)
    for chemin in ENDPOINTS.rglob("*.py"):
        if "__pycache__" in chemin.as_posix():
            continue
        for numero, ligne in enumerate(chemin.read_text(encoding="utf-8").splitlines(), 1):
            trouve = motif.search(ligne)
            if trouve:
                coupables.append(f"{chemin.name}:{numero} → {trouve.group(1)}.read()")

    assert not coupables, (
        "Lecture non bornee d'un fichier envoye — utiliser "
        "`storage.lire_borne(fichier, plafond)` :\n  " + "\n  ".join(coupables)
    )
