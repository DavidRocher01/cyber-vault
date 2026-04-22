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

    # Admin
    ADMIN_API_KEY: str = ""

    # HaveIBeenPwned API (breach checker)
    HIBP_API_KEY: str = ""

    # Number of trusted reverse proxies in front of the app.
    # 0 = no proxy (local dev), 1 = ALB only, 2 = CloudFront + ALB.
    # Determines how many IPs to strip from the right of X-Forwarded-For.
    TRUSTED_PROXY_COUNT: int = 1

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
