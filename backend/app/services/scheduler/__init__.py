"""Package scheduler — planification des jobs de fond (APScheduler).

`scheduler.py` monolithique (621 l., 7 domaines) découpé par domaine :
core (instance + start/stop), scans, ssl_alerts, newsletter, monthly_digest,
darkweb, awareness. L'API publique (`scheduler`, `start_scheduler`,
`stop_scheduler`) et les fonctions de job sont ré-exportées ici pour rester
importables via `app.services.scheduler`.
"""

from app.services.scheduler.awareness import _run_awareness_at_risk_detection
from app.services.scheduler.core import scheduler, start_scheduler, stop_scheduler
from app.services.scheduler.darkweb import _run_darkweb_monitoring
from app.services.scheduler.monthly_digest import _send_monthly_digest_job
from app.services.scheduler.newsletter import _send_biweekly_newsletter
from app.services.scheduler.scans import _schedule_due_scans
from app.services.scheduler.sites import _load_active_sites_with_last_scan
from app.services.scheduler.ssl_alerts import _check_ssl_alerts

__all__ = [
    "scheduler",
    "start_scheduler",
    "stop_scheduler",
    "_schedule_due_scans",
    "_check_ssl_alerts",
    "_send_biweekly_newsletter",
    "_send_monthly_digest_job",
    "_run_darkweb_monitoring",
    "_run_awareness_at_risk_detection",
    "_load_active_sites_with_last_scan",
]
