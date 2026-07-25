"""rgpd_delete_account_ondelete_fk_graph

Revision ID: eb7e53b74bfe
Revises: a08c087165b4
Create Date: 2026-07-25 19:12:54.548742

G0-2 — Effacement de compte RGPD (delete_account fait `db.delete(user)`).

Sans clause ON DELETE au niveau base, la suppression d'un utilisateur leve une
violation de cle etrangere (500) des qu'il possede des donnees liees. On pose
donc la strategie ON DELETE explicite sur tout le graphe FK atteignable depuis
`users` (et la chaine de 2e niveau via `sites`) :

  * CASCADE  : les donnees appartiennent au compte -> supprimees avec lui.
  * SET NULL : enregistrements a CONSERVER (obligation legale ou double role) ->
               on detache le lien personnel sans detruire l'enregistrement :
                 - invoices / quotes : retention comptable (~10 ans). Le droit a
                   l'effacement RGPD ne prime pas sur l'obligation legale de
                   conservation. La facture reste auto-suffisante (montant, numero,
                   identite client denormalisee, stripe_invoice_id) pour le CA.
                 - rssi_clients.client_user_id : PIEGE double role. La ligne
                   rssi_clients appartient au CONSULTANT (consultant_user_id). Si le
                   compte du CLIENT de portail est supprime, on ne doit surtout pas
                   detruire la fiche client du consultant -> on coupe juste le lien
                   de portail.
                 - sites.rssi_client_id : quand un consultant est supprime, ses
                   rssi_clients cascadent ; un site d'un AUTRE utilisateur pointant
                   vers cette fiche via rssi_client_id doit survivre lien coupe.

Les FK deja porteuses d'un ON DELETE (vault_item, notification, refresh_token,
phishing, password_reset_token, rssi_activity_log.user_id, awareness_*, finding_status,
etc.) ne sont pas touchees.

Les noms de contraintes sont introuvables de maniere deterministe (aucune
naming_convention, aucun nom explicite -> defaut Postgres {table}_{col}_fkey),
mais on introspecte le nom REEL au runtime pour rester robuste a toute divergence
entre environnements.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "eb7e53b74bfe"
down_revision: str | None = "a08c087165b4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# (table, colonne locale, table referencee, ondelete cible)
_FKS: list[tuple[str, str, str, str]] = [
    # --- FK vers users.id : CASCADE (donnees possedees par le compte) ---
    ("brand_profiles", "user_id", "users", "CASCADE"),
    ("code_scans", "user_id", "users", "CASCADE"),
    ("site_collaborators", "owner_user_id", "users", "CASCADE"),
    ("darkweb_dossiers", "user_id", "users", "CASCADE"),
    ("darkweb_scans", "user_id", "users", "CASCADE"),
    ("iso27001_assessments", "user_id", "users", "CASCADE"),
    ("nis2_assessments", "user_id", "users", "CASCADE"),
    ("sites", "user_id", "users", "CASCADE"),
    ("subscriptions", "user_id", "users", "CASCADE"),
    ("training_progress", "user_id", "users", "CASCADE"),
    ("url_scans", "user_id", "users", "CASCADE"),
    ("rssi_clients", "consultant_user_id", "users", "CASCADE"),
    # --- FK vers users.id : SET NULL (enregistrements conserves) ---
    ("invoices", "user_id", "users", "SET NULL"),
    ("quotes", "user_id", "users", "SET NULL"),
    ("rssi_clients", "client_user_id", "users", "SET NULL"),  # PIEGE double role
    # --- Chaine 2e niveau via sites.id : CASCADE ---
    ("scans", "site_id", "sites", "CASCADE"),
    ("site_collaborators", "site_id", "sites", "CASCADE"),
    # --- Chaine 2e niveau via rssi_clients.id : SET NULL (nullable) ---
    ("sites", "rssi_client_id", "rssi_clients", "SET NULL"),
]


def _existing_fk_name(inspector, table: str, column: str) -> str | None:
    """Nom reel de la contrainte FK monocolonne sur (table, column), sinon None."""
    for fk in inspector.get_foreign_keys(table):
        if fk.get("constrained_columns") == [column]:
            return fk.get("name")
    return None


def upgrade() -> None:
    # On PRESERVE le nom reel de chaque contrainte (certaines FK ont un nom
    # explicite non-standard, ex. fk_rssi_clients_client_user_id_users, dont le
    # downgrade d'une migration anterieure depend). On recree donc a l'identique,
    # en ajoutant seulement la clause ON DELETE.
    inspector = sa.inspect(op.get_bind())
    for table, column, ref_table, ondelete in _FKS:
        name = _existing_fk_name(inspector, table, column)
        if name is None:
            continue
        op.drop_constraint(name, table, type_="foreignkey")
        op.create_foreign_key(name, table, ref_table, [column], ["id"], ondelete=ondelete)


def downgrade() -> None:
    # Retour a l'etat initial : meme nom de contrainte, sans clause ON DELETE.
    inspector = sa.inspect(op.get_bind())
    for table, column, ref_table, _ondelete in _FKS:
        name = _existing_fk_name(inspector, table, column)
        if name is None:
            continue
        op.drop_constraint(name, table, type_="foreignkey")
        op.create_foreign_key(name, table, ref_table, [column], ["id"])
