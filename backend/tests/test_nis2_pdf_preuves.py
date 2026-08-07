"""Les pieces justificatives dans le document auditeur — etape 5f.

CE QUE CETTE ETAPE ACHEVE. Les etapes precedentes savaient stocker des pieces et
les rattacher a des criteres. Tant qu'elles n'apparaissaient pas dans l'export,
on stockait des documents sans dossier opposable : l'auditeur lisait des reponses
declarees sans savoir ce qui les appuyait.

LA REGLE QUI COMPTE LE PLUS ICI : une piece dont l'analyse antivirus n'est pas
concluante NE FIGURE PAS comme preuve. La presenter a un auditeur reviendrait a
la dire verifiee alors que la plateforme refuse elle-meme de la servir. Elle
n'est pas tue pour autant — le rapport annonce combien de documents ont ete
ecartes, sans quoi l'absence se lirait comme « rien n'a ete depose ».

COMMENT ON VERIFIE LE CONTENU SANS PARSER LE PDF. `pypdfium2` est volontairement
hors dependances du projet. On espionne donc `Paragraph` et `Table` dans le
module, comme le fait deja `test_nis2_unit`, et on lit ce qui leur est passe.

Cf. `docs/DEPOT_DOCUMENTS.md`.
"""

from datetime import UTC, datetime
from unittest.mock import patch

import pytest

import app.services.nis2_auditor_pdf as auditeur
from app.services.nis2_auditor_pdf import _pieces_retenues, generate_nis2_auditor_pdf
from app.services.nis2_catalogue import NIS2_CATEGORIES

MAINTENANT = datetime(2026, 8, 7, 12, 0, tzinfo=UTC)


def _piece(nom: str, statut: str = "sain") -> dict:
    return {
        "id": 1,
        "nom": nom,
        "taille_octets": 1024,
        "statut_analyse": statut,
        "rattache_le": MAINTENANT,
    }


def _rendu(pieces=None) -> tuple[bytes, str]:
    """Genere le document et rend (octets, tout le texte qui y a ete pose).

    On capture Paragraph ET Table : les intitules de section passent par le
    premier, les noms de documents par le second.
    """
    textes: list[str] = []
    vrai_p, vrai_t = auditeur.Paragraph, auditeur.Table

    def espion_p(texte, *a, **k):
        textes.append(str(texte))
        return vrai_p(texte, *a, **k)

    def espion_t(rows, *a, **k):
        for ligne in rows:
            textes.extend(str(cell) for cell in ligne)
        return vrai_t(rows, *a, **k)

    with (
        patch.object(auditeur, "Paragraph", espion_p),
        patch.object(auditeur, "Table", espion_t),
    ):
        pdf = generate_nis2_auditor_pdf(
            categories=NIS2_CATEGORIES,
            items={"rssi": "compliant", "policy": "partial"},
            score=42,
            user_email="abonne@test.com",
            updated_at=MAINTENANT,
            company_name="Entité de test",
            pieces=pieces,
        )
    return pdf, "\n".join(textes)


# ── Le tri entre ce qui est opposable et ce qui ne l'est pas ──────────────────


def test_seules_les_pieces_verifiees_sont_retenues():
    retenues, ecartees = _pieces_retenues(
        {
            "rssi": [_piece("bonne.pdf"), _piece("en_cours.pdf", "en_analyse")],
            "policy": [_piece("rejetee.pdf", "rejete")],
        }
    )

    assert [p["nom"] for p in retenues["rssi"]] == ["bonne.pdf"]
    assert "policy" not in retenues, "un critere sans piece retenue ne doit pas apparaitre"
    assert ecartees == 2


def test_un_statut_inconnu_n_est_jamais_retenu():
    """Meme regle que partout ailleurs : l'inconnu ne vaut pas « sain »."""
    retenues, ecartees = _pieces_retenues({"rssi": [_piece("bizarre.pdf", "PAS_VU")]})

    assert retenues == {}
    assert ecartees == 1


def test_sans_piece_le_tri_ne_leve_pas():
    assert _pieces_retenues(None) == ({}, 0)
    assert _pieces_retenues({}) == ({}, 0)


# ── Le document produit ──────────────────────────────────────────────────────


def test_le_document_se_genere_sans_piece():
    """La retrocompatibilite compte : l'export existait avant l'etape 5f."""
    pdf, _ = _rendu()
    assert pdf.startswith(b"%PDF-")
    assert len(pdf) > 5000


def test_le_nom_du_document_figure_dans_le_rapport():
    """Sans le nom, l'auditeur ne peut rattacher la piece a rien."""
    pdf, texte = _rendu({"rssi": [_piece("politique_securite.pdf")]})

    assert pdf.startswith(b"%PDF-")
    assert "politique_securite.pdf" in texte
    assert "Pièces justificatives fournies" in texte


def test_la_piece_est_rattachee_au_controle_qu_elle_appuie():
    """Un nom de fichier seul ne prouve rien : c'est le lien qui fait le dossier."""
    _, texte = _rendu({"rssi": [_piece("politique_securite.pdf")]})

    lignes = texte.splitlines()
    i = lignes.index("politique_securite.pdf")
    # Le tableau pose Domaine, Contrôle, Document dans cet ordre.
    assert "Gouvernance" in lignes[i - 2]
    assert "RSSI" in lignes[i - 1]


def test_une_piece_non_verifiee_n_apparait_pas_comme_preuve():
    """LE test de l'etape 5f."""
    _, texte = _rendu({"rssi": [_piece("pas_encore_analysee.pdf", "en_analyse")]})

    assert "pas_encore_analysee.pdf" not in texte


def test_les_pieces_ecartees_sont_annoncees():
    """ANNONCE, JAMAIS TU.

    Une omission muette laisserait croire que rien n'a ete depose pour ce
    controle, alors qu'un document attend simplement son verdict.
    """
    _, texte = _rendu({"rssi": [_piece("attente.pdf", "en_analyse")]})

    assert "vérification antivirus n'est pas concluante" in texte


def test_sans_aucune_piece_le_document_le_dit():
    """Il ne doit pas laisser croire a un dossier etaye qui n'existe pas."""
    _, texte = _rendu()

    assert "Aucune pièce justificative" in texte
    assert "déclaration de l'entité" in texte


def test_le_document_ne_prete_pas_de_valeur_probante_aux_pieces():
    """La plateforme verifie l'innocuite, pas le fond. Le dire evite un malentendu."""
    _, texte = _rendu({"rssi": [_piece("politique.pdf")]})

    assert "contenu n'a pas été analysé" in texte
    assert "revient à l'auditeur" in texte


def test_le_detail_par_categorie_compte_les_pieces():
    """Le tableau de detail gagne une colonne : un coup d'oeil suffit a voir
    quels controles sont appuyes."""
    _, texte = _rendu({"rssi": [_piece("a.pdf"), _piece("b.pdf")]})

    lignes = texte.splitlines()
    # L'en-tete du tableau de detail annonce la colonne.
    assert "Pièces" in lignes
    # Le critere « rssi » porte 2 pieces ; les autres affichent un tiret.
    i = lignes.index("Désignation d'un RSSI ou responsable cyber")
    assert lignes[i + 1] == "2"


# ── L endpoint alimente-t-il vraiment le generateur ? ─────────────────────────


@pytest.mark.asyncio
async def test_l_export_transmet_bien_les_pieces(db_session):
    """Le generateur peut etre parfait, encore faut-il que l'endpoint l'alimente."""
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    BASE = "/api/v1"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post(
            f"{BASE}/auth/register",
            json={"email": "pdf_preuve@test.com", "password": "StrongPass123!"},
        )
        r = await c.post(
            f"{BASE}/auth/login",
            json={"email": "pdf_preuve@test.com", "password": "StrongPass123!"},
        )
        h = {"Authorization": f"Bearer {r.json()['access_token']}"}

        depot = await c.post(
            f"{BASE}/nis2/me/criteres/rssi/pieces",
            headers=h,
            files={"fichier": ("preuve_rssi.pdf", b"%PDF-1.4 x", "application/pdf")},
        )
        assert depot.status_code == 201, depot.text

        with patch.object(
            auditeur, "generate_nis2_auditor_pdf", wraps=generate_nis2_auditor_pdf
        ) as gen:
            rep = await c.get(f"{BASE}/nis2/me/pdf/auditor", headers=h)

    assert rep.status_code == 200
    passees = gen.call_args.kwargs["pieces"]
    assert "rssi" in passees, "l'endpoint n'a pas transmis les pièces au générateur"
    assert passees["rssi"][0]["nom"] == "preuve_rssi.pdf"
