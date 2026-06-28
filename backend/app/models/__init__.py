# Import all models so SQLAlchemy Base.metadata is fully populated
from app.models.api_waitlist import ApiWaitlist  # noqa: F401
from app.models.app_setting import AppSetting  # noqa: F401
from app.models.awareness_badge import AwarenessBadge  # noqa: F401
from app.models.awareness_certificate import AwarenessCertificate  # noqa: F401
from app.models.awareness_enrollment import AwarenessEnrollment  # noqa: F401
from app.models.awareness_learner import AwarenessLearner  # noqa: F401
from app.models.awareness_learner_badge import AwarenessLearnerBadge  # noqa: F401
from app.models.awareness_module import AwarenessModule  # noqa: F401
from app.models.awareness_organization import AwarenessOrganization  # noqa: F401
from app.models.awareness_program import AwarenessProgram  # noqa: F401
from app.models.awareness_progress import AwarenessProgress  # noqa: F401
from app.models.awareness_quiz_attempt import AwarenessQuizAttempt  # noqa: F401
from app.models.blog_post import BlogPost  # noqa: F401
from app.models.booking import Booking  # noqa: F401
from app.models.booking_slot import BookingSlot  # noqa: F401
from app.models.brand_profile import BrandProfile  # noqa: F401
from app.models.breach_catalog import BreachCatalogEntry  # noqa: F401
from app.models.code_scan import CodeScan  # noqa: F401
from app.models.collab import SiteCollaborator  # noqa: F401
from app.models.contact_message import ContactMessage  # noqa: F401
from app.models.darkweb_dossier import DarkwebDossier, DarkwebDossierTarget  # noqa: F401
from app.models.darkweb_scan import DarkwebScan  # noqa: F401
from app.models.enums import (  # noqa: F401
    CampaignStatus,
    CollabStatus,
    ComplianceStatus,
    DossierStatus,
    EnrollmentStatus,
    FindingStatusEnum,
    InvoiceStatus,
    ProgressStatus,
    QuoteStatus,
    ScanStatus,
    SubscriptionStatus,
)
from app.models.finding_status import FindingStatus  # noqa: F401
from app.models.invoice import Invoice  # noqa: F401
from app.models.iso27001_assessment import Iso27001Assessment  # noqa: F401
from app.models.newsletter_schedule import NewsletterScheduleItem  # noqa: F401
from app.models.newsletter_subscriber import NewsletterSubscriber  # noqa: F401
from app.models.nis2_assessment import Nis2Assessment  # noqa: F401
from app.models.notification import Notification  # noqa: F401
from app.models.password_reset_token import PasswordResetToken  # noqa: F401
from app.models.phishing import (
    PhishingCampaign,
    PhishingDomainVerification,
    PhishingTarget,
)

# noqa: F401
from app.models.plan import Plan  # noqa: F401
from app.models.processed_stripe_event import ProcessedStripeEvent  # noqa: F401
from app.models.public_scan import PublicScan  # noqa: F401
from app.models.quote import Quote  # noqa: F401
from app.models.refresh_token import RefreshToken  # noqa: F401
from app.models.rssi_action import RssiAction  # noqa: F401
from app.models.rssi_client import RssiClient  # noqa: F401
from app.models.rssi_visit import RssiVisit  # noqa: F401
from app.models.scan import Scan  # noqa: F401
from app.models.site import Site  # noqa: F401
from app.models.subscription import Subscription  # noqa: F401
from app.models.training_progress import TrainingProgress  # noqa: F401
from app.models.url_scan import UrlScan  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.vault_item import VaultItem  # noqa: F401
