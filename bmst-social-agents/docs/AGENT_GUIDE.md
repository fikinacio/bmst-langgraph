# Adding a New Agent to BMST Social Agents

This guide walks through every step required to add a new agent to the pipeline using the
AOS (Agent Operating System) framework. Follow it in order — each step has a concrete
checklist.

---

## Step 1 — Define the AOS Identity Contract

Open [`aos-contracts.yaml`](../aos-contracts.yaml) and add a new entry under `agents:`.

```yaml
agents:
  - id: MY_NEW_AGENT
    name: "MY_NEW_AGENT"
    version: "1.0.0"
    description: "One sentence: what this agent does."
    scope: |
      What this agent is allowed to do and what it must never do.
    authority_levels:
      autonomous: ["list actions agent can take without human approval"]
      requires_approval: ["actions needing human sign-off"]
      prohibited: ["hard limits — never cross these"]
    inputs:
      - field: session_id
        type: str
        source: orchestrator
      # ... list every state field this agent reads
    outputs:
      - field: my_field
        type: MyPydanticModel
        description: What this field contains
      - field: action
        type: ActionType
      - field: status
        type: StatusType
      - field: confidence
        type: float
    fault_contract:
      EXECUTION_FAULT: "retry up to 3 times with backoff"
      CONFIDENCE_FAULT: "escalate to human if confidence < 0.X"
      SCHEMA_FAULT: "fail immediately, log error"
    hard_limits:
      - "Never publish without explicit approval"
      # add your agent-specific hard limits here
```

---

## Step 2 — Implement the agent node

Create a new package under `src/agents/`:

```
src/agents/my_new_agent/
├── __init__.py          # empty
└── node.py              # agent implementation
```

The `node.py` must expose a single async function with this exact signature:

```python
from src.orchestrator.state import SocialAgentState

async def my_new_agent_node(state: SocialAgentState) -> dict:
    """MY_NEW_AGENT — one line description."""
    ...
```

### Skeleton

```python
"""MY_NEW_AGENT — <description>.

Reads:  state["selected_topic"], state["posts"]
Writes: state["my_field"], action, status, confidence, errors
"""
import logging
from typing import Any

from src.config.settings import settings
from src.orchestrator.state import SocialAgentState
from src.protocols.fault_handler import FaultHandler
from src.protocols.io_schema import AgentOutput
from src.protocols.vocabulary import ActionType, FaultType, StatusType

logger = logging.getLogger(__name__)

_CONFIDENCE_THRESHOLD: float = 0.75


def _fault_state(fault_output: AgentOutput, error_context: Any) -> dict:
    return {
        "current_agent": "my_new_agent",
        "action": fault_output.action,
        "status": fault_output.status,
        "confidence": fault_output.confidence,
        "errors": [
            {
                "agent": "my_new_agent",
                "fault": fault_output.block_internal,
                "context": str(error_context)[:500],
            }
        ],
    }


async def my_new_agent_node(state: SocialAgentState) -> dict:
    """MY_NEW_AGENT — <description>."""
    session_id = state["session_id"]
    logger.info("MY_NEW_AGENT start", extra={"session_id": session_id})

    handler = FaultHandler()

    # Guard: check required state is present
    required = state.get("selected_topic")
    if required is None:
        return _fault_state(
            handler.handle(FaultType.CONFIDENCE_FAULT, {"step": "no_topic"}, retry_count=0),
            "no selected_topic in state",
        )

    # ... do your work here ...

    confidence = 1.0  # compute from your logic

    return {
        "current_agent": "my_new_agent",
        "my_field": ...,  # your output
        "action": ActionType.COMPLETE,
        "status": StatusType.TASK_COMPLETE,
        "confidence": confidence,
        "errors": [],
    }
```

### Conventions to follow

- Always set `"current_agent": "my_new_agent"` in every return path.
- Return a **dict**, never mutate the incoming `state`.
- Use `FaultHandler` for all error branches — never raise from a node.
- Log at `INFO` on entry, `WARNING` on partial failures, `ERROR` on faults.
- Confidence must be in `[0.0, 1.0]`. Use a formula that reflects actual quality.

---

## Step 3 — Add to the LangGraph graph

Open [`src/orchestrator/graph.py`](../src/orchestrator/graph.py) and add your node:

```python
from src.agents.my_new_agent.node import my_new_agent_node

# Inside build_graph():
graph.add_node("my_new_agent", my_new_agent_node)

# Wire edges — decide where your agent fits in the pipeline:
graph.add_edge("carousel", "my_new_agent")   # runs after CAROUSEL
graph.add_conditional_edges(
    "my_new_agent",
    router,
    {"revisor": "revisor", "end": END},
)
```

If your agent pauses for human input (like REVISOR does), add it to `interrupt_after`:

```python
compiled_graph = graph.compile(
    checkpointer=checkpointer,
    interrupt_after=["revisor", "my_new_agent"],  # add here
)
```

---

## Step 4 — Add routing logic

Open [`src/orchestrator/router.py`](../src/orchestrator/router.py) and add a case for your
agent's possible output actions:

```python
def router(state: SocialAgentState) -> str:
    agent = state.get("current_agent")
    action = state.get("action")

    # ... existing cases ...

    if agent == "my_new_agent":
        if action == ActionType.COMPLETE:
            return "revisor"
        if action == ActionType.ESCALATE_HUMAN:
            return END
        return END  # default safe exit

    # ...
```

---

## Step 5 — Create the evaluation dataset

Create `tests/datasets/my_new_agent_cases.yaml`:

```yaml
metadata:
  version: "1.0.0"
  agent: "my_new_agent"
  description: "Evaluation dataset for MY_NEW_AGENT."

cases:

  - id: "my_agent_hp_001"
    description: "Happy path: normal input, agent succeeds."
    agent_target: "my_new_agent"
    scenario_type: "happy_path"
    mocks:
      # values that will be patched during the test
      some_api_result: {"status": "ok"}
    input:
      session_id: "ds-my-agent-001"
      run_date: "2026-05-23"
      selected_topic:
        topic: "Test topic"
        source_url: "https://example.com"
        summary: "Test summary."
        relevance_score: 0.88
        content_angles: ["angle 1"]
        platforms_fit: [linkedin, instagram]
    expected_output:
      action: "complete"
      status: "task_complete"
      confidence_min: 0.80
      confidence_max: 1.00
    expected_behavior:
      should_escalate: false
      should_block: false
    tags: ["happy_path"]

  # Add at least 6 cases covering: happy_path, edge_case, fault_scenario
```

Minimum required cases per agent:
- 2 happy_path
- 2 edge_case
- 2 fault_scenario

---

## Step 6 — Write the parametrized test

Create `tests/test_my_new_agent.py` (or add to an existing file):

```python
"""Unit tests for MY_NEW_AGENT."""
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
import yaml

from src.agents.my_new_agent import node as my_agent
from src.protocols.vocabulary import ActionType, StatusType


def _load_cases(filename: str) -> list[dict]:
    path = Path(__file__).parent / "datasets" / filename
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)["cases"]


def _build_state(inp: dict) -> dict:
    # Build a full SocialAgentState from YAML input
    return {
        "session_id": inp.get("session_id", "ds-test"),
        "run_date": inp.get("run_date", "2026-05-23"),
        "research_briefs": [],
        "selected_topic": None,
        "selected_pillar": None,
        "posts": {},
        "carousel": None,
        "review_results": [],
        "pending_approval": False,
        "approval_decision": None,
        "revision_note": None,
        "revision_count": 0,
        "publication_results": [],
        "current_agent": "previous_agent",
        "action": ActionType.COMPLETE,
        "status": StatusType.TASK_COMPLETE,
        "confidence": 0.9,
        "errors": [],
    }


@pytest.mark.parametrize(
    "case", _load_cases("my_new_agent_cases.yaml"), ids=lambda c: c["id"]
)
async def test_my_new_agent_dataset(case):
    mocks = case.get("mocks", {})
    state = _build_state(case.get("input", {}))

    patches = [
        patch.object(my_agent.some_external_dep, "method",
                     new=AsyncMock(return_value=mocks.get("some_api_result"))),
    ]

    with ExitStack() as stack:
        for p in patches:
            stack.enter_context(p)
        result = await my_agent.my_new_agent_node(state)

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
```

Run your new tests: `pytest tests/test_my_new_agent.py -v`

---

## Step 7 — Update the README

In [`README.md`](../README.md):

1. Add a row to the **Agent responsibilities** table
2. Add a paragraph under **Agent descriptions**
3. Update the ASCII architecture diagram if the pipeline order changed
4. Add any new environment variables to the Prerequisites table

---

## AOS fault type reference

| Fault type | When to use | Default behaviour |
|------------|-------------|-------------------|
| `EXECUTION_FAULT` | External API call failed (network error, rate limit) | Retry up to 3× with backoff → escalate |
| `CONFIDENCE_FAULT` | No usable output (no search results, score too low) | Escalate to human immediately |
| `SCHEMA_FAULT` | LLM returned unparseable or invalid JSON | Fail immediately, no retry |
| `SAFETY_FAULT` | Security or policy violation detected | Fail immediately, alert human |
| `LOOP_FAULT` | Revision cycle exceeded maximum iterations | Terminate loop, escalate |

Always use `FaultHandler.handle(fault_type, context, retry_count)` — never construct
`AgentOutput` directly from a fault branch.

---

## Confidence scoring guidelines

| Score | Meaning |
|-------|---------|
| 0.90–1.00 | All criteria met, high quality |
| 0.75–0.89 | Minor issues, still publishable |
| 0.50–0.74 | Notable issues, revision recommended |
| 0.00–0.49 | Major issues, likely blocked |

The pipeline will escalate or block automatically when `confidence < CONFIDENCE_THRESHOLD`.
Each agent defines its own threshold; see the individual `node.py` for the value.
