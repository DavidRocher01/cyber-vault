"""Job newsletter Radar Cyber — `_send_biweekly_newsletter`, toutes les 2 semaines.

Trois choses peuvent mal tourner sans bruit ici :

- **Le compteur d'édition.** Il est lu puis réécrit en base ; s'il n'avance pas,
  chaque envoi repart de zéro, et les abonnés reçoivent deux fois « édition #1 ».
- **Le contenu éditorial**, stocké en base sous forme de JSON. Une saisie mal
  formée doit basculer sur le contenu par défaut — pas faire échouer l'envoi de
  toute la campagne.
- **Un destinataire en échec.** L'adresse d'un seul abonné ne doit pas priver
  tous les suivants de leur numéro.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.app_setting import AppSetting
from app.models.newsletter_subscriber import NewsletterSubscriber
from app.services.scheduler.newsletter import (
    _DEFAULT_NEWSLETTER_CONTENT,
    _NEWSLETTER_CONTENT_KEY,
    _NEWSLETTER_EDITION_KEY,
    _send_biweekly_newsletter,
)

MODULE = "app.services.scheduler.newsletter"


def _abonne(email: str = "abonne@exemple.fr", jeton: str = "jeton-1") -> MagicMock:
    s = MagicMock(spec=NewsletterSubscriber)
    s.email = email
    s.unsubscribe_token = jeton
    s.is_active = True
    return s


def _session(edition: int | None = None, contenu_texte: str | None = None, abonnes=()):
    """Session factice. `edition=None` simule une base sans compteur — le tout
    premier envoi."""
    reglages: dict[str, AppSetting] = {}
    if edition is not None:
        reglages[_NEWSLETTER_EDITION_KEY] = AppSetting(
            key=_NEWSLETTER_EDITION_KEY, value_int=edition
        )
    if contenu_texte is not None:
        reglages[_NEWSLETTER_CONTENT_KEY] = AppSetting(
            key=_NEWSLETTER_CONTENT_KEY, value_text=contenu_texte
        )

    db = AsyncMock()
    db.add = MagicMock()
    ajoutes: list[AppSetting] = []
    db.add.side_effect = ajoutes.append

    async def _get(_modele, cle):
        return reglages.get(cle)

    db.get = _get

    async def _execute(*_a, **_k):
        r = MagicMock()
        r.scalars.return_value.all.return_value = list(abonnes)
        return r

    db.execute = _execute

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=db)
    cm.__aexit__ = AsyncMock(return_value=False)
    return db, reglages, ajoutes, patch(f"{MODULE}.AsyncSessionLocal", MagicMock(return_value=cm))


# ─── compteur d'édition ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_premier_envoi_cree_le_compteur():
    db, _reglages, ajoutes, session = _session(edition=None, abonnes=[_abonne()])

    with session, patch("asyncio.to_thread", new_callable=AsyncMock) as envoi:
        await _send_biweekly_newsletter()

    assert len(ajoutes) == 1
    assert ajoutes[0].key == _NEWSLETTER_EDITION_KEY
    # Créé à 1, puis avancé à 2 pour la prochaine fois.
    assert ajoutes[0].value_int == 2
    assert envoi.call_args.kwargs["edition"] == 1


@pytest.mark.asyncio
async def test_le_compteur_avance_a_chaque_envoi():
    db, reglages, _ajoutes, session = _session(edition=7, abonnes=[_abonne()])

    with session, patch("asyncio.to_thread", new_callable=AsyncMock) as envoi:
        await _send_biweekly_newsletter()

    assert envoi.call_args.kwargs["edition"] == 7
    assert reglages[_NEWSLETTER_EDITION_KEY].value_int == 8


@pytest.mark.asyncio
async def test_le_compteur_avance_meme_sans_abonne():
    """Comportement constaté : le numéro d'édition est consommé même si
    personne ne la reçoit. Documenté ici pour qu'un changement soit délibéré."""
    db, reglages, _ajoutes, session = _session(edition=3, abonnes=[])

    with session, patch("asyncio.to_thread", new_callable=AsyncMock) as envoi:
        await _send_biweekly_newsletter()

    envoi.assert_not_called()
    assert reglages[_NEWSLETTER_EDITION_KEY].value_int == 4


# ─── contenu éditorial ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_contenu_par_defaut_si_rien_en_base():
    db, _r, _a, session = _session(edition=1, contenu_texte=None, abonnes=[_abonne()])

    with session, patch("asyncio.to_thread", new_callable=AsyncMock) as envoi:
        await _send_biweekly_newsletter()

    assert envoi.call_args.kwargs["flash_title"] == _DEFAULT_NEWSLETTER_CONTENT["flash_title"]


@pytest.mark.asyncio
async def test_contenu_personnalise_lu_en_base():
    perso = dict(_DEFAULT_NEWSLETTER_CONTENT, flash_title="Fuite massive chez un hébergeur")
    db, _r, _a, session = _session(edition=1, contenu_texte=json.dumps(perso), abonnes=[_abonne()])

    with session, patch("asyncio.to_thread", new_callable=AsyncMock) as envoi:
        await _send_biweekly_newsletter()

    assert envoi.call_args.kwargs["flash_title"] == "Fuite massive chez un hébergeur"


@pytest.mark.asyncio
async def test_json_illisible_retombe_sur_le_defaut_sans_lever():
    """Une saisie mal formée dans la console d'administration ne doit pas
    annuler la campagne."""
    db, _r, _a, session = _session(
        edition=1, contenu_texte="{ceci n'est pas du JSON", abonnes=[_abonne()]
    )

    with session, patch("asyncio.to_thread", new_callable=AsyncMock) as envoi:
        await _send_biweekly_newsletter()

    envoi.assert_called_once()
    assert envoi.call_args.kwargs["flash_title"] == _DEFAULT_NEWSLETTER_CONTENT["flash_title"]


# ─── envoi ───────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_un_envoi_par_abonne_avec_son_jeton():
    abonnes = [_abonne("a@exemple.fr", "jeton-a"), _abonne("b@exemple.fr", "jeton-b")]
    db, _r, _a, session = _session(edition=1, abonnes=abonnes)

    with session, patch("asyncio.to_thread", new_callable=AsyncMock) as envoi:
        await _send_biweekly_newsletter()

    assert envoi.call_count == 2
    destinataires = [appel.kwargs["to_email"] for appel in envoi.call_args_list]
    assert destinataires == ["a@exemple.fr", "b@exemple.fr"]

    # Le lien de désinscription est obligatoire et propre à chaque abonné :
    # un jeton partagé désabonnerait la mauvaise personne.
    liens = [appel.kwargs["unsubscribe_url"] for appel in envoi.call_args_list]
    assert "token=jeton-a" in liens[0]
    assert "token=jeton-b" in liens[1]


@pytest.mark.asyncio
async def test_un_echec_n_interrompt_pas_les_abonnes_suivants():
    abonnes = [_abonne("a@exemple.fr"), _abonne("b@exemple.fr"), _abonne("c@exemple.fr")]
    db, _r, _a, session = _session(edition=1, abonnes=abonnes)

    echecs = {"n": 0}

    async def _envoi(*_a, **_k):
        echecs["n"] += 1
        if echecs["n"] == 2:
            raise RuntimeError("adresse rejetée")

    with session, patch("asyncio.to_thread", _envoi):
        await _send_biweekly_newsletter()  # ne doit pas lever

    assert echecs["n"] == 3
