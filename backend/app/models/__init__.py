# Import all models so SQLAlchemy Base.metadata is fully populated
from app.models.user import User  # noqa: F401
from app.models.refresh_token import RefreshToken  # noqa: F401
from app.models.password_reset_token import PasswordResetToken  # noqa: F401
from app.models.vault_item import VaultItem  # noqa: F401
from app.models.plan import Plan  # noqa: F401
from app.models.subscription import Subscription  # noqa: F401
from app.models.site import Site  # noqa: F401
from app.models.scan import Scan  # noqa: F401
from app.models.newsletter_subscriber import NewsletterSubscriber  # noqa: F401
from app.models.url_scan import UrlScan  # noqa: F401
from app.models.notification import Notification  # noqa: F401
from app.models.newsletter_schedule import NewsletterScheduleItem  # noqa: F401
from app.models.code_scan import CodeScan  # noqa: F401
from app.models.nis2_assessment import Nis2Assessment  # noqa: F401
from app.models.iso27001_assessment import Iso27001Assessment  # noqa: F401
from app.models.app_setting import AppSetting  # noqa: F401
