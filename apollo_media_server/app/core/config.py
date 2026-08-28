from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str = "sqlite:////config/apollo.db"
    api_host: str = "0.0.0.0"
    api_port: int = 8099
    log_level: str = "info"
    version: str = "dev"

    model_config = SettingsConfigDict(env_prefix="APOLLO_", extra="ignore")

settings = Settings()
