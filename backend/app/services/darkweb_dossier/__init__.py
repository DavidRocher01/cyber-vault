"""
services/darkweb_dossier — Dark web dossier sub-package.

Re-exports the full public and internal API so that existing imports such as
    from app.services.darkweb_dossier_service import process_dossier, ...
continue to work via the darkweb_dossier_service.py shim.
"""

# Ingestion / processing
# Enrichment / scoring
from .enrichment import (
    _SEVERITY_WEIGHTS,
    _build_catalog_index,
    _build_recommendations,
    _compute_severity,
    sync_breach_catalog,
)
from .ingestion import (
    export_dossier_csv,
    process_dossier,
    send_darkweb_alert_email,
    send_monitoring_alert,
)

# Accès DB des dossiers (CRUD + rescan + monitoring)
from .queries import (
    count_user_dossiers,
    create_dossier_with_targets,
    delete_dossier,
    get_user_dossier,
    list_user_dossiers,
    reset_dossier_for_rescan,
    set_monitor,
)

# Reporting
from .reporting import generate_dossier_pdf

__all__ = [
    # public API
    "process_dossier",
    "generate_dossier_pdf",
    "export_dossier_csv",
    "sync_breach_catalog",
    "send_monitoring_alert",
    # DB access (dossier CRUD)
    "count_user_dossiers",
    "create_dossier_with_targets",
    "list_user_dossiers",
    "get_user_dossier",
    "delete_dossier",
    "reset_dossier_for_rescan",
    "set_monitor",
    # backward-compat alias
    "send_darkweb_alert_email",
    # internals (tests)
    "_compute_severity",
    "_build_recommendations",
    "_build_catalog_index",
    "_SEVERITY_WEIGHTS",
]
