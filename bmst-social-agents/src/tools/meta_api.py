"""Meta Graph API wrapper for Instagram and Facebook publishing.

Instagram publishing is a two-step container flow:
    1. POST /{ig_user_id}/media         → create a container holding the image+caption
    2. POST /{ig_user_id}/media_publish  → publish the container

Facebook page publishing is a single call to /{page_id}/photos or /{page_id}/feed.

Both flows reference image_url remotely (no binary upload needed). Retries
3× on 5xx with exponential backoff.
"""

import logging
from typing import Optional

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.config.settings import settings

logger = logging.getLogger(__name__)

_GRAPH_API_BASE = "https://graph.facebook.com/v19.0"


class MetaAPIError(Exception):
    """Raised when the Meta Graph API returns an error or is unreachable."""


_retry_http = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((httpx.HTTPError, MetaAPIError)),
    reraise=True,
)


# ---------------------------------------------------------------------------
# Instagram
# ---------------------------------------------------------------------------


@_retry_http
async def post_instagram(image_url: str, caption: str) -> dict:
    """Publish an image with caption to Instagram. Returns {post_url, id}.

    Raises:
        MetaAPIError if either step fails or settings are incomplete.
    """
    if not settings.instagram_access_token or not settings.instagram_account_id:
        raise MetaAPIError("Instagram credentials not configured")

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Step 1: create media container
        container_response = await client.post(
            f"{_GRAPH_API_BASE}/{settings.instagram_account_id}/media",
            data={
                "image_url": image_url,
                "caption": caption,
                "access_token": settings.instagram_access_token,
            },
        )
        _raise_on_error(container_response, step="instagram create container")
        container_id = container_response.json()["id"]
        logger.debug("Instagram container created", extra={"id": container_id})

        # Step 2: publish container
        publish_response = await client.post(
            f"{_GRAPH_API_BASE}/{settings.instagram_account_id}/media_publish",
            data={
                "creation_id": container_id,
                "access_token": settings.instagram_access_token,
            },
        )
        _raise_on_error(publish_response, step="instagram publish")
        post_id = publish_response.json()["id"]

    post_url = f"https://www.instagram.com/p/{post_id}/"
    logger.info("Instagram post published", extra={"post_id": post_id})
    return {"post_url": post_url, "id": post_id}


# ---------------------------------------------------------------------------
# Facebook
# ---------------------------------------------------------------------------


@_retry_http
async def post_facebook(
    message: str,
    image_url: Optional[str] = None,
) -> dict:
    """Publish a post to a Facebook Page. Returns {post_url, id}.

    If image_url is provided, posts to /photos (image post with message as caption).
    Otherwise posts text to /feed.

    Uses settings.facebook_page_id when set; otherwise falls back to
    settings.instagram_account_id (the page linked to the IG Business account).
    """
    if not settings.instagram_access_token:
        raise MetaAPIError("Meta access token not configured")

    page_id = settings.facebook_page_id or settings.instagram_account_id
    if not page_id:
        raise MetaAPIError(
            "Facebook page ID not configured "
            "(set FACEBOOK_PAGE_ID or INSTAGRAM_ACCOUNT_ID)"
        )

    endpoint = "photos" if image_url else "feed"
    payload = {
        "message": message,
        "access_token": settings.instagram_access_token,
    }
    if image_url:
        payload["url"] = image_url

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{_GRAPH_API_BASE}/{page_id}/{endpoint}",
            data=payload,
        )
        _raise_on_error(response, step=f"facebook {endpoint}")

    body = response.json()
    post_id = body.get("id") or body.get("post_id")
    post_url = f"https://www.facebook.com/{post_id}" if post_id else None
    logger.info("Facebook post published", extra={"post_id": post_id})
    return {"post_url": post_url, "id": post_id}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _raise_on_error(response: httpx.Response, step: str) -> None:
    """Raise MetaAPIError with context if the response is not 2xx.

    5xx errors are raised as MetaAPIError so the retry decorator catches them.
    4xx errors are also raised but logged differently (caller config issue).
    """
    if response.is_success:
        return

    body_preview = response.text[:300]
    if response.status_code >= 500:
        logger.error(
            "Meta server error",
            extra={"step": step, "status": response.status_code, "body": body_preview},
        )
    else:
        logger.error(
            "Meta client error",
            extra={"step": step, "status": response.status_code, "body": body_preview},
        )
    raise MetaAPIError(f"{step} {response.status_code}: {body_preview}")
