"""La grille tarifaire doit rester une source de verite unique.

Contexte : les `stripe_price_id` de production n'existaient nulle part dans le
depot. Ils avaient ete poses a la main en base, et les seules valeurs
versionnees etaient celles de trois migrations d'avril 2026 pointant des prix a
9,90 / 39,90 / 49,90 EUR. Une base reconstruite serait repartie en facturant
9,90 EUR un abonnement affiche 49 EUR.

Ces tests verrouillent les trois maillons : la grille, le seed, les migrations.
"""

import pathlib

import pytest
from sqlalchemy import select

from app.core.pricing import GRILLE, GRILLE_PAR_NOM, LIBELLES_RETIRES, PlanTarifaire
from app.models.plan import Plan

VERSIONS = pathlib.Path(__file__).resolve().parents[1] / "alembic" / "versions"


# ── La grille elle-meme ──────────────────────────────────────────────────────


class TestGrille:
    def test_quatre_paliers_ordonnes(self):
        assert [p.name for p in GRILLE] == ["free", "starter", "pro", "business"]
        assert [p.tier_level for p in GRILLE] == [1, 2, 3, 4]

    def test_prix_strictement_croissants(self):
        montants = [p.price_eur for p in GRILLE]
        assert montants == sorted(montants)
        assert len(set(montants)) == len(montants)

    def test_le_gratuit_ne_facture_rien(self):
        free = GRILLE_PAR_NOM["free"]
        assert free.price_eur == 0
        assert free.stripe_price_id == ""
        assert free.stripe_price_id_yearly == ""

    @pytest.mark.parametrize("nom", ["starter", "pro", "business"])
    def test_les_plans_payants_ont_leurs_deux_price_id(self, nom):
        """Un price_id annuel manquant desactive silencieusement la facturation
        annuelle (cf. `Plan.yearly_available`) — autant que ce soit deliberé."""
        plan = GRILLE_PAR_NOM[nom]
        assert plan.stripe_price_id.startswith("price_")
        assert plan.stripe_price_id_yearly.startswith("price_")
        assert plan.stripe_price_id != plan.stripe_price_id_yearly

    def test_price_id_jamais_partages_entre_plans(self):
        """Deux plans pointant le meme prix, c'est un palier facture au tarif
        d'un autre."""
        tous = [p.stripe_price_id for p in GRILLE if p.stripe_price_id]
        tous += [p.stripe_price_id_yearly for p in GRILLE if p.stripe_price_id_yearly]
        assert len(tous) == len(set(tous))

    def test_annuel_vaut_dix_mois(self):
        starter = GRILLE_PAR_NOM["starter"]
        assert starter.price_eur_yearly == starter.price_eur * 10

    def test_aucun_tarif_retire_ne_traine_dans_la_grille(self):
        montants = {f"{p.price_eur // 100},{p.price_eur % 100:02d}" for p in GRILLE}
        assert not (montants & set(LIBELLES_RETIRES))


# ── Le modele ORM doit calculer comme la grille ──────────────────────────────


def test_le_modele_et_la_grille_calculent_le_meme_annuel():
    """`Plan.price_eur_yearly` et `PlanTarifaire.price_eur_yearly` sont deux
    implementations de la meme regle commerciale. Elles doivent bouger ensemble."""
    for plan in GRILLE:
        orm = Plan(**{c: getattr(plan, c) for c in ("name", "price_eur")})
        assert orm.price_eur_yearly == plan.price_eur_yearly


# ── Les migrations doivent porter les identifiants courants ──────────────────


def test_chaque_price_id_de_la_grille_figure_dans_une_migration():
    """Sans cela, une base reconstruite repart sur des identifiants perimes.

    Ce test echoue des qu'un tarif change sans migration correspondante — ce qui
    force a en ecrire une nouvelle, jamais a retoucher une migration existante.
    """
    corpus = "\n".join(f.read_text(encoding="utf-8") for f in VERSIONS.glob("*.py"))
    manquants = [
        price_id
        for plan in GRILLE
        for price_id in (plan.stripe_price_id, plan.stripe_price_id_yearly)
        if price_id and price_id not in corpus
    ]
    assert not manquants, (
        "Ces price_id de la grille n'apparaissent dans aucune migration : "
        f"{manquants}. Ecrire une migration de donnees qui les pose."
    )


# ── Le seed doit produire exactement la grille ───────────────────────────────


@pytest.mark.asyncio
async def test_le_seed_produit_exactement_la_grille(db_session):
    """Le scenario « base neuve » de bout en bout : c'est celui qui etait casse."""
    from app.main import _seed_plans

    await _seed_plans()

    lignes = (await db_session.execute(select(Plan))).scalars().all()
    assert {ligne.name for ligne in lignes} == {p.name for p in GRILLE}

    for ligne in lignes:
        attendu: PlanTarifaire = GRILLE_PAR_NOM[ligne.name]
        assert ligne.price_eur == attendu.price_eur
        assert ligne.max_sites == attendu.max_sites
        assert ligne.scan_interval_days == attendu.scan_interval_days
        assert ligne.tier_level == attendu.tier_level
        assert ligne.allow_conformity_export == attendu.allow_conformity_export
        assert ligne.stripe_price_id == attendu.stripe_price_id
        assert ligne.stripe_price_id_yearly == attendu.stripe_price_id_yearly


@pytest.mark.asyncio
async def test_le_seed_ne_recrase_pas_un_plan_existant(db_session):
    """La production peut avoir des price_id poses a la main. Un redemarrage ne
    doit pas les remplacer — le seed n'insere que ce qui manque."""
    from app.main import _seed_plans

    await _seed_plans()
    ligne = (await db_session.execute(select(Plan).where(Plan.name == "starter"))).scalar_one()
    ligne.stripe_price_id = "price_pose_a_la_main"
    await db_session.commit()

    await _seed_plans()

    relu = (await db_session.execute(select(Plan).where(Plan.name == "starter"))).scalar_one()
    assert relu.stripe_price_id == "price_pose_a_la_main"
