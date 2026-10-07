from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    project_name: str = "ArtGallery API"
    database_url: str = "postgresql+psycopg2://artgallery:artgallery@db:5432/artgallery"

    secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24

    cors_origins: str = "http://localhost:3000"

    upload_dir: str = "uploads"
    max_upload_mb: int = 5
    max_photos_per_artwork: int = 10

    admin_email: str = "admin@artgallery.md"
    admin_password: str = "admin12345"
    seed_demo_data: bool = True

    db_connect_retries: int = 30
    db_connect_delay_sec: float = 2.0

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
