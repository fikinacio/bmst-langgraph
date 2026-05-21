"""Canva REST API wrapper for generating carousel slides and post images.

The filename retains the "mcp" suffix from the original spec, but the
implementation uses Canva's REST API directly via httpx — not an MCP server.

Workflow per asset (autofill template → export):
    1. POST  /rest/v1/autofills           → start an autofill job
    2. GET   /rest/v1/autofills/{job_id}  → poll until status == "success"
    3. POST  /rest/v1/exports             → start an export job
    4. GET   /rest/v1/exports/{job_id}    → poll until status == "success"
    5. Return the export URL.

This module returns None (not raises) on Canva errors so the CAROUSEL agent
can fall back to a placeholder image without breaking the pipeline.
"""

import asyncio
import logging
from typing import Optional

import httpx

from src.config.settings import settings
from src.protocols.vocabulary import Platform

logger = logging.getLogger(__name__)

_CANVA_BASE_URL = "https://api.canva.com/rest/v1"

# Default BMST brand colours — override per call if needed
DEFAULT_BRAND_COLORS: dict[str, str] = {
    "azure": "#1a4a6b",
    "teal": "#2a8a7a",
    "orange": "#d4601a",
}

# Polling settings for async Canva jobs
_POLL_INTERVAL_SECONDS = 2.0
_POLL_MAX_ATTEMPTS = 30  # 60s ceiling total


class CanvaError(Exception):
    """Raised internally when a Canva job fails. Caller methods catch and return None."""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def generate_carousel_slide(
    headline: str,
    body: str,
    visual_brief: str,
    brand_colors: Optional[dict[str, str]] = None,
    slide_number: int = 1,
    total_slides: int = 1,
) -> Optional[str]:
    """Generate a single carousel slide and return its CDN URL.

    Returns None if Canva is unconfigured or any step fails.
    """
    if not settings.canva_api_token or not settings.canva_brand_kit_id:
        logger.warning("Canva unconfigured, skipping slide generation")
        return None

    colors = brand_colors or DEFAULT_BRAND_COLORS
    autofill_data = {
        "headline": {"type": "text", "text": headline},
        "body": {"type": "text", "text": body},
        "visual_brief": {"type": "text", "text": visual_brief},
        "slide_position": {"type": "text", "text": f"{slide_number}/{total_slides}"},
        "color_primary": {"type": "text", "text": colors.get("azure", "#1a4a6b")},
        "color_accent": {"type": "text", "text": colors.get("teal", "#2a8a7a")},
    }

    try:
        return await _autofill_and_export(
            template_label="carousel_slide",
            autofill_data=autofill_data,
        )
    except CanvaError as exc:
        logger.error("Canva carousel slide failed", extra={"error": str(exc)})
        return None


async def generate_post_image(
    caption_brief: str,
    platform: Platform,
    brand_colors: Optional[dict[str, str]] = None,
) -> Optional[str]:
    """Generate a single platform-sized post image and return its CDN URL.

    Returns None if Canva is unconfigured or any step fails.
    """
    if not settings.canva_api_token or not settings.canva_brand_kit_id:
        logger.warning("Canva unconfigured, skipping post image")
        return None

    colors = brand_colors or DEFAULT_BRAND_COLORS
    autofill_data = {
        "caption_brief": {"type": "text", "text": caption_brief},
        "platform": {"type": "text", "text": platform.value},
        "color_primary": {"type": "text", "text": colors.get("azure", "#1a4a6b")},
        "color_accent": {"type": "text", "text": colors.get("orange", "#d4601a")},
    }

    try:
        return await _autofill_and_export(
            template_label=f"post_{platform.value}",
            autofill_data=autofill_data,
        )
    except CanvaError as exc:
        logger.error("Canva post image failed", extra={"error": str(exc)})
        return None


# ---------------------------------------------------------------------------
# Private: the autofill → poll → export → poll workflow
# ---------------------------------------------------------------------------


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.canva_api_token}",
        "Content-Type": "application/json",
    }


async def _autofill_and_export(
    template_label: str,
    autofill_data: dict,
) -> str:
    """Run the full autofill + export workflow and return the export URL.

    Raises CanvaError on any step failure. The public methods catch this
    and return None.
    """
    logger.debug("Canva autofill start", extra={"template": template_label})

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Step 1: start autofill
        autofill_response = await client.post(
            f"{_CANVA_BASE_URL}/autofills",
            json={
                "brand_template_id": settings.canva_brand_kit_id,
                "data": autofill_data,
                "title": template_label,
            },
            headers=_headers(),
        )
        if not autofill_response.is_success:
            raise CanvaError(
                f"autofill start {autofill_response.status_code}: "
                f"{autofill_response.text[:200]}"
            )
        autofill_id = autofill_response.json()["job"]["id"]

        # Step 2: poll autofill until done
        design_id = await _poll_job(
            client=client,
            url=f"{_CANVA_BASE_URL}/autofills/{autofill_id}",
            result_key="design",
            sub_key="id",
        )

        # Step 3: start export
        export_response = await client.post(
            f"{_CANVA_BASE_URL}/exports",
            json={"design_id": design_id, "format": {"type": "png"}},
            headers=_headers(),
        )
        if not export_response.is_success:
            raise CanvaError(
                f"export start {export_response.status_code}: "
                f"{export_response.text[:200]}"
            )
        export_id = export_response.json()["job"]["id"]

        # Step 4: poll export until done — result is the URL of the first page
        urls = await _poll_job(
            client=client,
            url=f"{_CANVA_BASE_URL}/exports/{export_id}",
            result_key="urls",
        )
        if not urls:
            raise CanvaError("export completed with no URLs")

        return urls[0] if isinstance(urls, list) else urls


async def _poll_job(
    client: httpx.AsyncClient,
    url: str,
    result_key: str,
    sub_key: Optional[str] = None,
):
    """Poll a Canva job URL until status == success or terminal failure.

    Returns job["{result_key}"] (or job[result_key][sub_key] when provided).
    Raises CanvaError on timeout or terminal failure.
    """
    for attempt in range(_POLL_MAX_ATTEMPTS):
        response = await client.get(url, headers=_headers())
        if not response.is_success:
            raise CanvaError(
                f"poll {url} {response.status_code}: {response.text[:200]}"
            )

        body = response.json().get("job", {})
        status = body.get("status")

        if status == "success":
            value = body.get(result_key)
            if sub_key and isinstance(value, dict):
                return value.get(sub_key)
            return value

        if status == "failed":
            raise CanvaError(f"job failed: {body.get('error', 'no error detail')}")

        await asyncio.sleep(_POLL_INTERVAL_SECONDS)

    raise CanvaError(f"polling timed out after {_POLL_MAX_ATTEMPTS} attempts")
