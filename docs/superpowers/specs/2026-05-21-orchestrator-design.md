# LangGraph Orchestrator — Design Spec

**Goal:** Implement the LangGraph state machine that wires SCOUT → WRITER → CAROUSEL → REVISOR → PUBLISHER, with an HITL interrupt after REVISOR.

**Tech:** LangGraph ≥0.2, MemorySaver checkpointer, TypedDict state, conditional edges.

---

## Files

### `src/orchestrator/state.py`
`SocialAgentState(TypedDict)` with all fields per prompt. Imports `ResearchBrief`, `PlatformPost`, `CarouselOutput`, `ReviewResult`, `PublicationResult` from `io_schema` and `ActionType`, `StatusType` from `vocabulary`. The `errors` field uses `Annotated[list[dict], operator.add]` so error entries accumulate across nodes; every other collection field uses default replacement semantics.

### `src/orchestrator/router.py`
Five pure functions. Constants `_CONFIDENCE_THRESHOLD = 0.70` and `_MAX_REVISIONS = 3` at module level. Routing follows the prompt verbatim; `"escalate"` from `route_after_scout` maps to `END` in the graph edges (the agent's `block_internal` carries the escalation note for n8n to act on).

### `src/orchestrator/graph.py`
`build_graph()` constructs the `StateGraph(SocialAgentState)` and adds all nodes + conditional edges. Module-level `compiled_graph = build_graph().compile(checkpointer=MemorySaver(), interrupt_after=["revisor"])`. `async def run_graph(session_id) -> SocialAgentState` builds the initial state with `date.today().isoformat()`, sets `thread_id = session_id` in the config, and calls `await compiled_graph.ainvoke(initial_state, config=config)`.

### Stub agent nodes — 5 files under `src/agents/*/node.py`
Each defines `async def {agent}_node(state) -> dict` returning a minimal state delta so the graph compiles and runs end-to-end. These get replaced when real agents are implemented.

---

## Key Decisions

1. **`interrupt_after=["revisor"]`** — REVISOR runs the AI quality check first, persists to `review_log` with `human_decision=NULL`, then the graph pauses. On resume the router reads `approval_decision` and continues.
2. **`MemorySaver`** — per the prompt. Note this is in-memory and won't survive a process restart; for production HITL persistence consider `PostgresSaver` in a follow-up.
3. **`errors` accumulates** — every other field replaces, so a re-entry into WRITER (via `revision_requested`) overwrites the previous post.
4. **Carousel failure is graceful** — `route_after_carousel` always returns `"revisor"`; REVISOR is responsible for handling the case where `state["carousel"] is None`.
5. **`"wait"` from `route_after_revisor`** — maps to `END` in graph edges. With `interrupt_after`, the natural pause happens between revisor execution and edge evaluation; the `"wait"` path only fires if the graph is resumed without an `approval_decision`, in which case ending is the safe default.
