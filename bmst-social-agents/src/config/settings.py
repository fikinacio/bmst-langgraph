"""Application settings loaded from environment variables.

Required variables cause a ValidationError at import time if missing.
Optional integration variables (Canva, LinkedIn, Instagram, Langfuse, Brave)
default to None and are validated at agent invocation time.

Usage:
    from src.config.settings import settings
    print(settings.anthropic_api_key)
"""

import re
from typing import Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All configuration for bmst-social-agents, grouped by integration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ── Anthropic ────────────────────────────────────────────────────────────
    anthropic_api_key: str

    # ── Internal API ─────────────────────────────────────────────────────────
    bmst_api_key: str

    # ── App ──────────────────────────────────────────────────────────────────
    app_env: str = "development"
    log_level: str = "INFO"

    # ── Redis ─────────────────────────────────────────────────────────────────
    redis_url: str = "redis://redis:6379"

    # ── Supabase ──────────────────────────────────────────────────────────────
    supabase_url: str
    supabase_service_key: str

    # ── Evolution API (WhatsApp) ───────────────────────────────────────────────
    evolution_api_url: str
    evolution_api_key: str
    evolution_instance: str
    revisor_approver_phone: str
    revisor_approval_timeout_seconds: int = 3600

    # ── SCOUT agent ───────────────────────────────────────────────────────────
    # Tavily is purpose-built for AI agents: native relevance scoring and
    # article-extract endpoint.
    tavily_api_key: Optional[str] = None
    scout_rss_feeds: str = ""  # comma-separated URLs
    scout_lookback_days: int = 1
    scout_max_articles: int = 10

    # ── REVISOR agent — AI-content detection ─────────────────────────────────
    # GPTZero primary; Claude heuristic is the fallback when this is unset
    # or the API call fails.
    gptzero_api_key: Optional[str] = None

    # ── WRITER agent ──────────────────────────────────────────────────────────
    writer_model: str = "claude-sonnet-4-6"
    writer_max_tokens: int = 1024
    writer_language: str = "pt"

    # ── CAROUSEL agent ────────────────────────────────────────────────────────
    canva_api_token: Optional[str] = None
    canva_brand_kit_id: Optional[str] = None
    # Brand template ID — distinct from brand kit. Canva separates the layout
    # (template) from the colours/fonts (brand kit). Required for autofill.
    canva_template_id: Optional[str] = None
    carousel_default_slides: int = 5

    # ── PUBLISHER agent — LinkedIn ─────────────────────────────────────────────
    linkedin_client_id: Optional[str] = None
    linkedin_client_secret: Optional[str] = None
    linkedin_access_token: Optional[str] = None
    linkedin_org_urn: Optional[str] = None

    # ── PUBLISHER agent — Instagram ────────────────────────────────────────────
    instagram_access_token: Optional[str] = None
    instagram_account_id: Optional[str] = None

    # ── PUBLISHER agent — Facebook ─────────────────────────────────────────────
    # Set this when the Facebook page being published to is different from the
    # one linked to the Instagram Business account. Falls back to
    # instagram_account_id in meta_api.post_facebook() when unset.
    facebook_page_id: Optional[str] = None

    # ── Langfuse (observability) ───────────────────────────────────────────────
    langfuse_public_key: Optional[str] = None
    langfuse_secret_key: Optional[str] = None
    langfuse_host: str = "https://cloud.langfuse.com"

    # ── Scheduler ─────────────────────────────────────────────────────────────
    scheduler_cron: str = "0 7 * * 1-5"
    scheduler_timezone: str = "Africa/Luanda"

    # ── Validators ────────────────────────────────────────────────────────────

    @field_validator("revisor_approver_phone")
    @classmethod
    def validate_phone_e164(cls, v: str) -> str:
        """E.164 format: + followed by 7 to 15 digits, first digit non-zero."""
        if not re.match(r"^\+[1-9]\d{6,14}$", v):
            raise ValueError(
                "revisor_approver_phone must be E.164 format: "
                "+ followed by 7–15 digits (e.g. +41795748225)"
            )
        return v

    @field_validator("supabase_url", "evolution_api_url", "langfuse_host")
    @classmethod
    def validate_http_url(cls, v: str) -> str:
        """Ensure HTTP/HTTPS URLs are well-formed and strip trailing slashes."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("must be a valid http:// or https:// URL")
        return v.rstrip("/")

    @field_validator("redis_url")
    @classmethod
    def validate_redis_url(cls, v: str) -> str:
        """Redis DSN must start with redis:// or rediss:// (TLS)."""
        if not v.startswith(("redis://", "rediss://")):
            raise ValueError("redis_url must start with redis:// or rediss://")
        return v

    @property
    def rss_feed_list(self) -> list[str]:
        """Parse the comma-separated SCOUT_RSS_FEEDS string into a list."""
        return [url.strip() for url in self.scout_rss_feeds.split(",") if url.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


settings = Settings()
