import os
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    database_url: str = ""
    secret_key: str = "change-this-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 480
    debug: bool = True
    log_level: str = "DEBUG"
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

@lru_cache
def get_settings():
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    s = Settings()
    if not s.database_url:
        db_path = os.path.join(base, "data.db").replace("\\", "/")
        s.database_url = f"sqlite:///{db_path}"
    return s
