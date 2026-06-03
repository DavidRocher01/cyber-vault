from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Cyber-Vault"
    APP_ENV: str = "development"
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    DATABASE_URL: str

    ALLOWED_ORIGINS: list[str] = ["http://localhost:4200", "http://localhost:4201"]

    # Sécurité login
    MAX_LOGIN_ATTEMPTS: int = 5
    LOCKOUT_MINUTES: int = 15

    # Observabilité
    SENTRY_DSN: str | None = None

    # Stripe
    STRIPE_SECRET_KEY: str = ""
    STRIPE_PUBLISHABLE_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""

    # Frontend URL (pour redirections Stripe)
    FRONTEND_URL: str = "http://localhost:4200"

    # Email SMTP (fallback local dev)
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 465
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""

    @property
    def smtp_from_address(self) -> str:
        return self.SMTP_FROM or self.SMTP_USER

    # Email transactionnel Resend
    RESEND_API_KEY: str = ""
    RESEND_FROM: str = "CyberScan <no-reply@cyberscanapp.com>"

    # S3 file storage (livrables RSSI)
    S3_BUCKET_NAME: str = ""
    AWS_REGION: str = "eu-west-3"
    # AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY lues automatiquement par boto3
    # (variables d'env standard ou IAM role ECS en prod)

    # Admin
    ADMIN_API_KEY: str = ""

    # Contact form recipient
    CONTACT_EMAIL: str = "contact@cyberscanapp.com"

    # HaveIBeenPwned API (breach checker)
    HIBP_API_KEY: str = ""

    # Phishing simulation engine (homemade, no GoPhish)
    # Base URL used for tracking pixel / click / landing routes (served by this API)
    # Set to https://sim.cyberscanapp.com in prod; https://api.cyberscanapp.com also works
    PHISHING_BASE_URL: str = "https://sim.cyberscanapp.com"
    # Sender identity in phishing emails (display name only — actual domain must be Resend-verified)
    PHISHING_FROM_EMAIL: str = ""  # e.g. no-reply@cyberscanapp.com (Resend verified domain)
    PHISHING_FROM_NAME: str = "CyberScan Exercise"
    # Batch size: emails sent per scheduler tick (every 15 min) to avoid spam detection
    PHISHING_BATCH_SIZE: int = 20
    # How many days tracking links remain active after campaign launch (then events are silently dropped)
    PHISHING_TRACKING_TTL_DAYS: int = 30

    # Add-on extra sites pack (5 slots per pack, monthly)
    ADDON_EXTRA_SITES_STRIPE_PRICE_ID: str = ""
    ADDON_EXTRA_SITES_COUNT: int = 5
    ADDON_EXTRA_SITES_PRICE_EUR: int = 900  # 9.00€/month

    # Number of trusted reverse proxies in front of the app.
    # 0 = no proxy (local dev), 1 = ALB only, 2 = CloudFront + ALB.
    # Determines how many IPs to strip from the right of X-Forwarded-For.
    TRUSTED_PROXY_COUNT: int = 1

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
