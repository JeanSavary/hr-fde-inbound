from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    api_key: str = "dev-api-key-change-me"
    fmcsa_web_key: str = ""
    app_name: str = "Acme Logistics API"
    brokerage_name: str = "Acme Logistics"
    agent_name: str = "John"
    default_search_radius_miles: int = 75

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
