"""TikTok publishing — STUB.

TikTok's Content Posting API requires OAuth2 with a specific scope, plus a
two-step upload flow (initialise upload → resumable PUT → publish). It's
deferred until BMST has a working developer account.

PUBLISHER calls this conditionally and currently records a TikTok attempt
as PublicationResult(status='manual_delivery') without invoking this file.
The function below exists so that future implementation has a clear entry
point — and so any code that accidentally tries to call it gets a loud
NotImplementedError instead of a silent failure.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class TikTokError(Exception):
    """Raised when the TikTok API returns an error or the implementation is missing."""


async def post_tiktok(
    video_url: str,
    caption: str,
    cover_image_url: Optional[str] = None,
) -> dict:
    """Publish a video to TikTok.

    Args:
        video_url:        Publicly reachable URL of the video to publish.
        caption:          Caption text including any hashtags.
        cover_image_url:  Optional cover thumbnail URL.

    Returns:
        {"post_url": str, "id": str} on success.

    Raises:
        NotImplementedError: TikTok integration is not implemented yet.

    # TODO: implement the TikTok Content Posting API workflow:
    #   1. POST  /v2/post/publish/inbox/video/init/   → upload_id, upload_url
    #   2. PUT   {upload_url}                         → uploads the bytes
    #   3. POST  /v2/post/publish/status/fetch/       → poll until published
    #   4. Return the resulting post URL.
    """
    logger.error(
        "TikTok publishing called but not implemented",
        extra={"caption_preview": caption[:80]},
    )
    raise NotImplementedError(
        "TikTok publishing is not implemented. PUBLISHER currently records "
        "TikTok attempts as status='manual_delivery' without calling this function."
    )
