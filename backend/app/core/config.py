from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Cyber-Vault"
    APP_ENV: str = "development"
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    DATABASE_URL: str

    ALLOWED_ORIGINS: list[str] = ["http://localhost:4200"]

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
