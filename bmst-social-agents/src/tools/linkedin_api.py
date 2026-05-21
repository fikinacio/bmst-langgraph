"""LinkedIn API v2 wrapper for company-page posting with optional image.

Workflow when an image is supplied (three calls):
    1. POST /rest/images?action=initializeUpload  → returns upload URL + image URN
    2. PUT  {upload_url} (binary)                  → uploads the image bytes
    3. POST /rest/posts                            → creates the post referencing the URN

When no image is supplied, only step 3 runs with no media.

Retries: 3× on 5xx with exponential backoff.
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

_LINKEDIN_BASE_URL = "https://api.linkedin.com"
_LINKEDIN_API_VERSION = "202401"


class LinkedInError(Exception):
    """Raised when the LinkedIn API returns an error or is unreachable."""


_retry_http = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((httpx.HTTPError, LinkedInError)),
    reraise=True,
)


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.linkedin_access_token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
        "LinkedIn-Version": _LINKEDIN_API_VERSION,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


@_retry_http
async def post_linkedin(
    text: str,
    image_url: Optional[str] = None,
) -> dict:
    """Publish a post on the configured LinkedIn organisation page.

    Returns {post_url, id} on success.
    Raises LinkedInError on config or HTTP failures.
    """
    if not settings.linkedin_access_token or not settings.linkedin_org_urn:
        raise LinkedInError("LinkedIn credentials not configured")

    async with httpx.AsyncClient(timeout=30.0) as client:
        image_urn = None
        if image_url:
            image_urn = await _upload_image(client, image_url)

        post_body = _build_post_body(text, image_urn)
        response = await client.post(
            f"{_LINKEDIN_BASE_URL}/rest/posts",
            json=post_body,
            headers=_headers(),
        )
        _raise_on_error(response, step="linkedin create post")

    # LinkedIn returns the post URN in the x-restli-id header
    post_urn = response.headers.get("x-restli-id") or response.json().get("id")
    post_id = post_urn.split(":")[-1] if post_urn else None
    post_url = (
        f"https://www.linkedin.com/feed/update/{post_urn}/" if post_urn else None
    )
    logger.info("LinkedIn post published", extra={"post_urn": post_urn})
    return {"post_url": post_url, "id": post_id}


# ---------------------------------------------------------------------------
# Image upload (3-step LinkedIn flow)
# ---------------------------------------------------------------------------


async def _upload_image(client: httpx.AsyncClient, image_url: str) -> str:
    """Run the LinkedIn image-upload flow and return the image URN.

    LinkedIn image upload requires us to first fetch the bytes ourselves
    (LinkedIn doesn't accept a remote image_url like Meta does).
    """
    # Step 1: fetch image bytes from the source URL
    image_response = await client.get(image_url, timeout=30.0)
    if not image_response.is_success:
        raise LinkedInError(
            f"failed to fetch source image {image_response.status_code}"
        )
    image_bytes = image_response.content

    # Step 2: initialize upload to get a target URL + URN
    init_response = await client.post(
        f"{_LINKEDIN_BASE_URL}/rest/images?action=initializeUpload",
        json={"initializeUploadRequest": {"owner": settings.linkedin_org_urn}},
        headers=_headers(),
    )
    _raise_on_error(init_response, step="linkedin init upload")
    init_body = init_response.json()["value"]
    upload_url = init_body["uploadUrl"]
    image_urn = init_body["image"]

    # Step 3: PUT the bytes to the upload URL
    put_headers = {"Authorization": f"Bearer {settings.linkedin_access_token}"}
    put_response = await client.put(
        upload_url, content=image_bytes, headers=put_headers, timeout=60.0
    )
    _raise_on_error(put_response, step="linkedin upload bytes")
    logger.debug("LinkedIn image uploaded", extra={"urn": image_urn})

    return image_urn


def _build_post_body(text: str, image_urn: Optional[str]) -> dict:
    """Construct the /rest/posts request body, with or without a media URN."""
    body: dict = {
        "author": settings.linkedin_org_urn,
        "commentary": text,
        "visibility": "PUBLIC",
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": [],
        },
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
    }
    if image_urn:
        body["content"] = {"media": {"id": image_urn}}
    return body


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _raise_on_error(response: httpx.Response, step: str) -> None:
    """Raise LinkedInError with context if the response is not 2xx."""
    if response.is_success:
        return

    body_preview = response.text[:300]
    if response.status_code >= 500:
        logger.error(
            "LinkedIn server error",
            extra={"step": step, "status": response.status_code, "body": body_preview},
        )
    else:
        logger.error(
            "LinkedIn client error",
            extra={"step": step, "status": response.status_code, "body": body_preview},
        )
    raise LinkedInError(f"{step} {response.status_code}: {body_preview}")
