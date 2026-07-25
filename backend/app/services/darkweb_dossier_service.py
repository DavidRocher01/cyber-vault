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
    count_user_dossiers,
    create_dossier_with_targets,
    delete_dossier,
    export_dossier_csv,
    generate_dossier_pdf,
    get_user_dossier,
    list_user_dossiers,
    process_dossier,
    reset_dossier_for_rescan,
    send_darkweb_alert_email,
    send_monitoring_alert,
    set_monitor,
    sync_breach_catalog,
)
