from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://bank_erp:change-me@localhost:5432/bank_erp"

    initial_admin_login: str = "admin"
    initial_admin_password: str = ""

    cookie_secure: bool = False
    session_ttl_hours: int = 8

    # сканы документов (сертификаты); в контейнере — том uploads
    upload_dir: str = "/data/uploads"

    # защита от перебора паролей
    login_max_failures: int = 5
    login_lock_minutes: int = 15


settings = Settings()
