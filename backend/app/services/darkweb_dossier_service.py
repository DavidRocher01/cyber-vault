"""
darkweb_dossier_service.py — compatibility shim.

The implementation has been moved to the services/darkweb_dossier/ sub-package.
This module re-exports everything so that existing imports continue to work:

    from app.services.darkweb_dossier_service import process_dossier, ...
"""

from app.services.darkweb_dossier import (  # noqa: F401  (re-export)
    _SEVERITY_WEIGHTS,
    _build_catalog_index,
    _build_recommendations,
    _compute_severity,
    export_dossier_csv,
    generate_dossier_pdf,
    process_dossier,
    send_darkweb_alert_email,
    send_monitoring_alert,
    sync_breach_catalog,
)
