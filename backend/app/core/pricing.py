"""Grille tarifaire — source de vérité unique.

Ce module existe parce que les `stripe_price_id` de production n'existaient
**nulle part dans le dépôt** : ils avaient été posés à la main en base via
`scripts/set_stripe_price_ids.py`, et les seules valeurs versionnées étaient
celles de trois vieilles migrations, périmées depuis la refonte du 2026-07-26.
Une base reconstruite depuis zéro serait donc repartie avec les identifiants
d'avril — c'est-à-dire en facturant 9,90 € un abonnement affiché 49 €.

Tout ce qui touche au prix part d'ici :
  - le seed de démarrage (`app.main._seed_plans`) ;
  - la migration qui aligne les bases déjà en service ;
  - la garde de facturation (`app.services.stripe_service`), qui refuse de
    créer une session de paiement dont le montant ne correspond pas.

**Changer un tarif** : modifier `GRILLE` ici, créer les prix correspondants
chez Stripe, reporter les `price_...`, ajouter les anciens montants à
`LIBELLES_RETIRES`, écrire une migration de données. La marche à suivre
complète est dans `docs/RELEASE_RUNBOOK.md`.

Les `price_...` ne sont pas des secrets : ils transitent en clair jusqu'au
navigateur lors du checkout. Les versionner est sans risque, et c'est le seul
moyen qu'une base restaurée reparte sur la bonne facturation.
"""

from dataclasses import dataclass

# Facturation annuelle : douze mois d'usage, dix mois payés.
MOIS_FACTURES_A_L_ANNEE = 10

# Comportement TVA des prix Stripe. Les six prix LIVE sont en `inclusive`, et
# c'est un choix, pas un oubli.
#
# Rocher Cybersécurité est aujourd'hui en franchise en base de TVA (art. 293 B
# du CGI) : aucune TVA n'est collectée, HT = TTC. La grille de juillet 2026
# (49 / 149 / 390 €) a été relevée **en avance de phase**, pour que les prix
# affichés n'aient PAS à bouger le jour où la franchise tombera. Ce jour-là,
# `inclusive` fera exactement ce qu'on attend : le client continuera de payer
# 49 €, dont la TVA sera reversée — l'absorption des 20 % est délibérée et déjà
# financée par la hausse.
#
# Ne pas « corriger » ce réglage en `exclusive` : cela ferait payer 58,80 € au
# lieu de 49 € et casserait la promesse de stabilité tarifaire. `tax_behavior`
# étant immuable chez Stripe, une bascule imposerait en plus de recréer les six
# prix.
#
# Ce qui restera à faire au passage à la TVA, en revanche : les CGV et les pages
# publiques annoncent des prix « HT », ce qui est exact sous franchise mais
# deviendra faux — 49 € TTC valant 40,83 € HT. C'est le libellé qu'il faudra
# reprendre, pas les montants.
#
# La garde de facturation compare cette constante au prix réel avant tout débit :
# tant que les deux disent la même chose, la situation est celle qu'on croit.
COMPORTEMENT_TVA_ATTENDU = "inclusive"


@dataclass(frozen=True, slots=True)
class PlanTarifaire:
    """Une ligne de la grille. Les montants sont en centimes."""

    name: str
    display_name: str
    price_eur: int
    max_sites: int  # -1 = illimité
    scan_interval_days: int
    tier_level: int
    allow_conformity_export: bool
    stripe_price_id: str = ""
    stripe_price_id_yearly: str = ""

    @property
    def price_eur_yearly(self) -> int:
        """Doit rester aligné sur `Plan.price_eur_yearly` (modèle ORM)."""
        return self.price_eur * MOIS_FACTURES_A_L_ANNEE


# Grille tranchée le 2026-07-26. Les `price_...` sont ceux du compte LIVE, et
# ce sont les seuls encore actifs : les sept générations précédentes ont été
# archivées chez Stripe le 2026-08-02.
GRILLE: tuple[PlanTarifaire, ...] = (
    PlanTarifaire(
        name="free",
        display_name="Gratuit",
        price_eur=0,
        max_sites=1,
        scan_interval_days=30,
        tier_level=1,
        # Dégustation : auto-évaluation possible, export PDF verrouillé.
        allow_conformity_export=False,
    ),
    PlanTarifaire(
        name="starter",
        display_name="Surveillance Starter",
        price_eur=4900,
        max_sites=5,
        scan_interval_days=1,
        tier_level=2,
        allow_conformity_export=True,
        stripe_price_id="price_1TxQ6B1kFVtkWldS5UuJBANP",
        stripe_price_id_yearly="price_1TxQ6Z1kFVtkWldS2NK9MR3v",
    ),
    PlanTarifaire(
        name="pro",
        display_name="Surveillance Pro",
        price_eur=14900,
        max_sites=25,
        scan_interval_days=1,
        tier_level=3,
        allow_conformity_export=True,
        stripe_price_id="price_1TxQ811kFVtkWldS6j432oEy",
        stripe_price_id_yearly="price_1TxQ8K1kFVtkWldSuwGN0x5K",
    ),
    PlanTarifaire(
        name="business",
        display_name="Surveillance Business",
        price_eur=39000,
        max_sites=-1,
        scan_interval_days=1,
        tier_level=4,
        allow_conformity_export=True,
        stripe_price_id="price_1TxQ9Z1kFVtkWldS3zxEZK9H",
        stripe_price_id_yearly="price_1TxQA91kFVtkWldS3cxc9zMa",
    ),
)

GRILLE_PAR_NOM: dict[str, PlanTarifaire] = {plan.name: plan for plan in GRILLE}

# Montants publiquement annoncés par le passé, écrits en toutes lettres dans les
# pages vitrines et les articles de blog. `scripts/check_prix_retires.py` échoue
# si l'un d'eux réapparaît dans une surface visible par un prospect : c'est
# exactement comme ça qu'un article annonçait encore 9,90 € huit mois après.
# Ajouter ici les anciens montants à chaque changement de grille.
LIBELLES_RETIRES: tuple[str, ...] = (
    "9,90",  # Starter, avril 2026
    "14,90",  # Starter, juin 2026
    "39,90",  # Pro, avril 2026
    "49,90",  # Business, avril 2026
)


def seed_plan_kwargs(plan: PlanTarifaire) -> dict[str, object]:
    """Champs à insérer dans `plans` — les noms suivent le modèle ORM."""
    return {
        "name": plan.name,
        "display_name": plan.display_name,
        "price_eur": plan.price_eur,
        "max_sites": plan.max_sites,
        "scan_interval_days": plan.scan_interval_days,
        "tier_level": plan.tier_level,
        "allow_conformity_export": plan.allow_conformity_export,
        "stripe_price_id": plan.stripe_price_id,
        "stripe_price_id_yearly": plan.stripe_price_id_yearly,
    }
