from pathlib import Path                      # NEW (add at top)

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    genx_root: str = str(Path(__file__).resolve().parents[1])   # CHANGED (was ".")
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 1440
    database_url: str = "sqlite:///./genx.db"
    allowed_origins: str = "http://localhost:3000"
    resend_api_key: str = ""
    resend_from_email: str = "GenX <noreply@genx.vortech.markets>"
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    flutterwave_secret_key: str = ""
    flutterwave_webhook_hash: str = ""
    @property
    def allowed_origins_list(self) -> List[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]

    class Config:
        env_file = ".env"


settings = Settings()