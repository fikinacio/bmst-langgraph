# core/settings.py — Application settings loaded from environment / .env file

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    All configuration is read from environment variables (or .env file).
    Field names match the keys in .env.example exactly.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",   # silently ignore unknown env vars
    )

    # ── API ───────────────────────────────────────────────────────────────────
    BMST_API_KEY: str = ""
    APP_ENV: str = "development"

    # ── Anthropic ─────────────────────────────────────────────────────────────
    ANTHROPIC_API_KEY: str = ""

    # ── Redis ─────────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379"

    # ── Supabase ──────────────────────────────────────────────────────────────
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_KEY: str = ""

    # ── Google Sheets ─────────────────────────────────────────────────────────
    GOOGLE_SHEETS_ID: str = ""
    GOOGLE_SERVICE_ACCOUNT_JSON: str = ""

    # ── Evolution API (WhatsApp) ──────────────────────────────────────────────
    EVOLUTION_API_URL: str = "http://localhost:8080"
    EVOLUTION_API_KEY: str = ""
    EVOLUTION_INSTANCE: str = "bmst"

    # ── Telegram ──────────────────────────────────────────────────────────────
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""

    # ── Langfuse ──────────────────────────────────────────────────────────────
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_HOST: str = "https://cloud.langfuse.com"

    # ── Gotenberg (PDF generation) ────────────────────────────────────────────
    GOTENBERG_URL: str = "http://gotenberg:3000"

    # ── Notion (DELIVERY workspace creation) ──────────────────────────────────
    NOTION_TOKEN: str = ""
    NOTION_DATABASE_ID: str = ""   # parent DB where project pages are created

    # ── InvoiceNinja (LEDGER billing) ─────────────────────────────────────────
    INVOICENINJA_URL: str = "http://invoiceninja"
    INVOICENINJA_KEY: str = ""

    # ── HUNTER behaviour ──────────────────────────────────────────────────────
    HUNTER_MAX_MESSAGES_PER_DAY: int = 20
    HUNTER_DELAY_BETWEEN_MESSAGES: int = 90   # seconds between WA sends


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings singleton — reads .env once on first call."""
    return Settings()


# Module-level alias for convenient import: `from core.settings import settings`
settings = get_settings()
