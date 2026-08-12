import os
from dataclasses import dataclass
from dotenv import load_dotenv
load_dotenv()


@dataclass(frozen=True)
class Settings:
    supabase_url: str = os.getenv("SUPABASE_URL", "")
    supabase_key: str = os.getenv("SUPABASE_PUBLISHABLE_KEY", "")

    frontend_url: str = os.getenv(
        "FRONTEND_URL",
        "https://andromeda-teal.vercel.app",
    )

    @property
    def cors_origins(self) -> list[str]:
        configured = os.getenv("CORS_ORIGINS", self.frontend_url)
        origins = [origin.strip().rstrip("/") for origin in configured.split(",")]
        origins.extend([
            "https://andromeda-teal.vercel.app",
            "http://localhost:5500",
        ])
        return list(dict.fromkeys(origin for origin in origins if origin))

    cookie_secure: bool = os.getenv("COOKIE_SECURE","false").lower() == "true"

    cookie_samesite: str = os.getenv("COOKIE_SAMESITE","lax")


settings = Settings()

if not settings.supabase_url or not settings.supabase_key:
    raise RuntimeError("SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY must be configured")
