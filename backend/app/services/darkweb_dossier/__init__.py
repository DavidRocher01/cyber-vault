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

# Reporting
from .reporting import generate_dossier_pdf

__all__ = [
    # public API
    "process_dossier",
    "generate_dossier_pdf",
    "export_dossier_csv",
    "sync_breach_catalog",
    "send_monitoring_alert",
    # backward-compat alias
    "send_darkweb_alert_email",
    # internals (tests)
    "_compute_severity",
    "_build_recommendations",
    "_build_catalog_index",
    "_SEVERITY_WEIGHTS",
]
