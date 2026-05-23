"""Unit tests for the CAROUSEL agent node.

External dependencies (AsyncAnthropic, canva_mcp.generate_carousel_slide)
are stubbed so tests run without network or credentials.
"""

import json
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml
from pydantic import ValidationError

from src.agents.carousel import node as carousel
from src.protocols.io_schema import CarouselOutput, CarouselSlide, PlatformPost, ResearchBrief
from src.protocols.vocabulary import ActionType, Platform, StatusType


def _load_cases(filename: str) -> list[dict]:
    path = Path(__file__).parent / "datasets" / filename
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)["cases"]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_brief() -> ResearchBrief:
    return ResearchBrief(
        topic="Automação em PMEs angolanas",
        source_url="https://example.com/article",
        summary="PMEs em Angola estão a adoptar fluxos automáticos.",
        relevance_score=0.85,
        content_angles=[
            "ROI de processos digitais",
            "Casos práticos em escritórios",
            "Erros comuns ao começar",
        ],
        platforms_fit=[Platform.INSTAGRAM, Platform.LINKEDIN],
    )


@pytest.fixture
def base_state(sample_brief) -> dict:
    return {
        "session_id": "test-carousel-001",
        "run_date": "2026-05-21",
        "research_briefs": [sample_brief],
        "selected_topic": sample_brief,
        "posts": {},
        "carousel": None,
        "review_results": [],
        "pending_approval": False,
        "approval_decision": None,
        "revision_note": None,
        "revision_count": 0,
        "publication_results": [],
        "current_agent": "writer",
        "action": ActionType.REQUEST_APPROVAL,
        "status": StatusType.TASK_COMPLETE,
        "confidence": 0.9,
        "errors": [],
    }


def _make_slide_dict(
    n: int,
    *,
    headline: str | None = None,
    body: str | None = None,
) -> dict:
    """Build a CarouselSlide-shaped dict. Slide 1 = hook, last = CTA by default."""
    return {
        "slide_number": n,
        "headline": headline or f"Headline slide {n}",
        "body": body or f"Body content for slide {n}, kept short and concrete.",
        "visual_brief": f"Visual direction for slide {n}",
        "canva_asset_url": None,
    }


def _make_carousel_payload(n_slides: int = 5) -> dict:
    """Build a full CarouselOutput-shaped dict with hook + body + CTA structure."""
    slides = []
    # Slide 1: hook ends with ?
    slides.append(
        _make_slide_dict(
            1,
            headline="A pergunta que muda tudo",
            body="Está a perder horas em tarefas que um sistema podia fazer sozinho?",
        )
    )
    # Middle body slides
    for i in range(2, n_slides):
        slides.append(_make_slide_dict(i))
    # Last slide: CTA
    slides.append(
        _make_slide_dict(
            n_slides,
            headline="Próximo passo",
            body="Contacte a BMST e descubra como automação muda o jogo no seu negócio.",
        )
    )
    return {
        "carousel_title": "Automação para PMEs em Angola",
        "platform": "instagram",
        "slides": slides,
        "caption": "Como pôr a automação a trabalhar para si. Para Instagram e LinkedIn.",
        "hashtags": ["#bmst", "#angola", "#empreender", "#tech"],
    }


def _fake_claude_response(payload: dict) -> MagicMock:
    response = MagicMock()
    response.content = [MagicMock(text=json.dumps(payload, ensure_ascii=False))]
    return response


def _patch_anthropic_and_canva(fake_response: MagicMock, canva_urls: list[str | None]):
    """Patch AsyncAnthropic and canva_mcp.generate_carousel_slide for one test."""
    mock_llm = MagicMock()
    mock_llm.messages = MagicMock()
    mock_llm.messages.create = AsyncMock(return_value=fake_response)

    # Each successive call to generate_carousel_slide returns the next URL
    canva_iter = iter(canva_urls)

    async def _fake_canva(**kwargs):
        try:
            return next(canva_iter)
        except StopIteration:
            return None

    anth_patch = patch.object(carousel, "AsyncAnthropic", return_value=mock_llm)
    canva_patch = patch.object(
        carousel.canva_mcp,
        "generate_carousel_slide",
        new=AsyncMock(side_effect=_fake_canva),
    )
    return anth_patch, canva_patch, mock_llm


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_carousel_structure_valid(base_state):
    """Happy path: 5 slides, all Canva images succeed, confidence = 1.0."""
    payload = _make_carousel_payload(n_slides=5)
    urls = [f"https://canva.example/slide_{i}.png" for i in range(1, 6)]
    anth_patch, canva_patch, _ = _patch_anthropic_and_canva(_fake_claude_response(payload), urls)

    with anth_patch, canva_patch:
        result = await carousel.carousel_node(base_state)

    assert result["current_agent"] == "carousel"
    assert result["status"] == StatusType.TASK_COMPLETE
    assert result["action"] == ActionType.COMPLETE
    assert result["confidence"] == pytest.approx(1.0)

    out: CarouselOutput = result["carousel"]
    assert isinstance(out, CarouselOutput)
    assert len(out.slides) == 5
    assert all(s.canva_asset_url and s.canva_asset_url.startswith("https://") for s in out.slides)
    assert out.platform == Platform.INSTAGRAM


def test_carousel_slide_count_limits():
    """Pydantic enforces 3 ≤ slides ≤ 10; CAROUSEL parses 5/7/10 cleanly.

    Boundaries below and above the schema bounds raise ValidationError so
    CAROUSEL's parse step would translate them to SCHEMA_FAULT.
    """
    # Schema bounds — 2 slides rejected (below min_length=3)
    payload_too_few = _make_carousel_payload(n_slides=5)
    payload_too_few["slides"] = payload_too_few["slides"][:2]
    with pytest.raises(ValidationError):
        CarouselOutput(**payload_too_few)

    # 11 slides rejected (above max_length=10)
    payload_too_many = _make_carousel_payload(n_slides=10)
    # Append one more slide to push to 11
    extra = _make_slide_dict(11)
    payload_too_many["slides"].append(extra)
    with pytest.raises(ValidationError):
        CarouselOutput(**payload_too_many)

    # Within bounds — 5, 7, 10 all parse cleanly
    for n in (5, 7, 10):
        CarouselOutput(**_make_carousel_payload(n_slides=n))


async def test_carousel_canva_failure_resilience(base_state):
    """Two of five Canva calls return None → status still TASK_COMPLETE,
    confidence drops per formula, those slides retain canva_asset_url=None."""
    payload = _make_carousel_payload(n_slides=5)
    # Slide 2 and slide 4 fail (None); 1, 3, 5 succeed
    urls = [
        "https://canva.example/slide_1.png",
        None,
        "https://canva.example/slide_3.png",
        None,
        "https://canva.example/slide_5.png",
    ]
    anth_patch, canva_patch, _ = _patch_anthropic_and_canva(_fake_claude_response(payload), urls)

    with anth_patch, canva_patch:
        result = await carousel.carousel_node(base_state)

    # Agent does not fault on image failures
    assert result["status"] == StatusType.TASK_COMPLETE

    # Confidence formula: 1.0 - 0.15 * 2 = 0.70
    assert result["confidence"] == pytest.approx(0.70)

    out: CarouselOutput = result["carousel"]
    assert out.slides[0].canva_asset_url == "https://canva.example/slide_1.png"
    assert out.slides[1].canva_asset_url is None
    assert out.slides[2].canva_asset_url == "https://canva.example/slide_3.png"
    assert out.slides[3].canva_asset_url is None
    assert out.slides[4].canva_asset_url == "https://canva.example/slide_5.png"


def test_carousel_first_slide_is_hook():
    """Heuristic: slide 1's body ends with '?' or starts with an imperative verb.

    NOTE: hook quality is enforced by the system prompt,
    not by code. This test only checks structural heuristics
    (question mark or imperative opening). A slide can pass
    this check and still be a weak hook — that is caught by
    REVISOR's quality scoring, not here.
    """
    imperatives = ("descubra", "imagine", "considere", "saiba", "veja", "pense", "olhe")

    def is_hook_like(text: str) -> bool:
        t = text.strip().lower()
        return t.endswith("?") or any(t.startswith(v) for v in imperatives)

    # Question-style hook → passes
    assert is_hook_like("Está a perder horas em tarefas repetitivas?") is True
    # Imperative-style hook → passes
    assert is_hook_like("Imagine o seu negócio sem trabalho manual.") is True
    # Plain declarative → fails this heuristic (REVISOR catches semantic weakness)
    assert is_hook_like("A automação está a mudar o trabalho.") is False

    # The payload our other tests use should pass this heuristic on slide 1
    payload = _make_carousel_payload(n_slides=5)
    first = payload["slides"][0]
    assert is_hook_like(first["body"]) is True


def test_carousel_last_slide_has_cta():
    """Heuristic: the final slide body contains a recognised CTA keyword."""
    cta_keywords = {
        "contacte", "siga", "comenta", "saiba mais",
        "bmst", "fidelinacio", "fidel kussunga",
    }

    def has_cta(text: str) -> bool:
        return any(kw in text.lower() for kw in cta_keywords)

    assert has_cta("Contacte a BMST hoje.") is True
    assert has_cta("Siga o Fidel para mais conteúdos.") is True
    assert has_cta("Texto puramente informativo, sem CTA.") is False

    # The default payload's last slide should pass
    payload = _make_carousel_payload(n_slides=5)
    last = payload["slides"][-1]
    assert has_cta(last["body"]) is True


# ---------------------------------------------------------------------------
# Dataset-driven tests
# ---------------------------------------------------------------------------


def _build_carousel_state(inp: dict) -> dict:
    """Build SocialAgentState for the CAROUSEL node from YAML input overrides."""
    topic_raw = inp.get("selected_topic")
    selected_topic = ResearchBrief(**topic_raw) if topic_raw else None

    posts_raw = inp.get("posts", {})
    posts = {
        plat: PlatformPost(**data) for plat, data in posts_raw.items()
    } if posts_raw else {}

    return {
        "session_id": inp.get("session_id", "ds-carousel-test"),
        "run_date": inp.get("run_date", "2026-05-23"),
        "research_briefs": [selected_topic] if selected_topic else [],
        "selected_topic": selected_topic,
        "selected_pillar": inp.get("selected_pillar"),
        "posts": posts,
        "carousel": None,
        "review_results": [],
        "pending_approval": False,
        "approval_decision": None,
        "revision_note": None,
        "revision_count": 0,
        "publication_results": [],
        "current_agent": "writer",
        "action": ActionType.REQUEST_APPROVAL,
        "status": StatusType.TASK_COMPLETE,
        "confidence": 0.9,
        "errors": [],
    }


@pytest.mark.parametrize("case", _load_cases("carousel_cases.yaml"), ids=lambda c: c["id"])
async def test_carousel_dataset(case):
    """Parametrized test driven by tests/datasets/carousel_cases.yaml."""
    mocks = case.get("mocks", {})
    state = _build_carousel_state(case.get("input", {}))

    claude_carousel = mocks.get("claude_carousel", {})
    canva_urls = mocks.get("canva_urls", [])

    fake_resp = MagicMock()
    fake_resp.content = [MagicMock(text=json.dumps(claude_carousel, ensure_ascii=False))]

    mock_llm = MagicMock()
    mock_llm.messages = MagicMock()
    mock_llm.messages.create = AsyncMock(return_value=fake_resp)

    url_iter = iter(canva_urls)

    async def _fake_canva(**kwargs):
        try:
            return next(url_iter)
        except StopIteration:
            return None

    with (
        patch.object(carousel, "AsyncAnthropic", return_value=mock_llm),
        patch.object(
            carousel.canva_mcp, "generate_carousel_slide",
            new=AsyncMock(side_effect=_fake_canva),
        ),
    ):
        result = await carousel.carousel_node(state)

    exp = case["expected_output"]
    result_action = result["action"].value if hasattr(result["action"], "value") else result["action"]
    result_status = result["status"].value if hasattr(result["status"], "value") else result["status"]

    assert result_action == exp["action"], (
        f"[{case['id']}] action: got {result_action!r}, want {exp['action']!r}"
    )
    assert result_status == exp["status"], (
        f"[{case['id']}] status: got {result_status!r}, want {exp['status']!r}"
    )
    conf = result.get("confidence", 0)
    assert exp["confidence_min"] <= conf <= exp["confidence_max"], (
        f"[{case['id']}] confidence {conf} not in "
        f"[{exp['confidence_min']}, {exp['confidence_max']}]"
    )

    behavior = case["expected_behavior"]
    if behavior.get("should_escalate"):
        assert result_action == "escalate_human", (
            f"[{case['id']}] expected escalation, got action={result_action!r}"
        )
    if behavior.get("should_block"):
        assert result_status in ("blocked", "failed"), (
            f"[{case['id']}] expected block/fail, got status={result_status!r}"
        )
