from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "Private Club"
    database_url: str = "sqlite:///./club.db"
    secret_key: str = "change-me"
    telegram_bot_token: str = ""
    telegram_bot_username: str = ""
    public_base_url: str = "http://localhost:8000"
    rules_version: str = "1.0"
    verification_retention_days: int = 7
    max_profile_photos: int = 6
    redis_url: str = "redis://redis:6379/0"
    session_ttl_seconds: int = 86400
    s3_endpoint: str = "minio:9000"
    s3_access_key: str = "privateclub"
    s3_secret_key: str = "change-me"
    s3_bucket: str = "private-club-media"
    s3_secure: bool = False
    staff_telegram_ids: str = ""
    staff_totp_secret: str = ""
    environment: str = "development"
    clamav_host: str = ""
    clamav_port: int = 3310
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
