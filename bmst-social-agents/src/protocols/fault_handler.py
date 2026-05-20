"""Stateless fault handler for the AOS protocol layer.

The handler returns an AgentOutput describing what the calling agent should do
next. It does not sleep or retry internally — backoff delays are communicated
to the caller via block_internal so the agent graph node can implement the wait.
"""

import logging
from datetime import datetime, timezone

from src.protocols.io_schema import AgentOutput
from src.protocols.vocabulary import ActionType, FaultType, StatusType

logger = logging.getLogger(__name__)

# Retry limits
_MAX_EXECUTION_RETRIES = 3
_MAX_LOOP_ITERATIONS = 3

# Exponential backoff delay in seconds per retry attempt (1-indexed)
_EXECUTION_BACKOFF: dict[int, int] = {1: 2, 2: 4, 3: 8}


class FaultHandler:
    """Translate faults into typed AgentOutput instructions.

    All methods are synchronous and stateless. The retry_count argument
    is maintained by the calling agent graph node, not here.
    """

    def handle(
        self, fault_type: FaultType, context: dict, retry_count: int
    ) -> AgentOutput:
        """Return the appropriate AgentOutput for the given fault.

        Args:
            fault_type: Category of fault that occurred.
            context:    Arbitrary key-value context for logging (never logged in full).
            retry_count: How many times this fault has already been handled.

        Returns:
            AgentOutput instructing the agent what to do next.
        """
        logger.error(
            "Agent fault",
            extra={
                "fault_type": fault_type.value,
                "retry_count": retry_count,
                "context_keys": list(context.keys()),
            },
        )

        now = datetime.now(timezone.utc)

        if fault_type == FaultType.SAFETY_FAULT:
            return self._safety_fault(now)

        if fault_type == FaultType.EXECUTION_FAULT:
            return self._execution_fault(now, retry_count)

        if fault_type == FaultType.LOOP_FAULT:
            return self._loop_fault(now, retry_count)

        if fault_type == FaultType.CONFIDENCE_FAULT:
            return self._confidence_fault(now)

        # SCHEMA_FAULT and SCOPE_FAULT: fail immediately, no retry
        return AgentOutput(
            block_client=None,
            block_internal=(
                f"{fault_type.value.upper()}: unrecoverable fault, no retry. "
                f"Context keys: {list(context.keys())}"
            ),
            action=ActionType.FAIL,
            status=StatusType.FAILED,
            confidence=0.0,
            timestamp=now,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _safety_fault(self, now: datetime) -> AgentOutput:
        """SAFETY_FAULT bypasses all retry logic and escalates immediately."""
        return AgentOutput(
            block_client=None,
            block_internal=(
                "SAFETY_FAULT: content safety violation detected. "
                "Immediate human escalation required. No retry."
            ),
            action=ActionType.ESCALATE_HUMAN,
            status=StatusType.FAILED,
            confidence=0.0,
            timestamp=now,
        )

    def _execution_fault(self, now: datetime, retry_count: int) -> AgentOutput:
        """EXECUTION_FAULT retries up to 3 times with exponential backoff."""
        attempt = retry_count + 1
        if retry_count < _MAX_EXECUTION_RETRIES:
            delay = _EXECUTION_BACKOFF.get(attempt, 8)
            return AgentOutput(
                block_client=None,
                block_internal=(
                    f"EXECUTION_FAULT: attempt {attempt}/{_MAX_EXECUTION_RETRIES}. "
                    f"Wait {delay}s before retrying."
                ),
                action=ActionType.WAIT,
                status=StatusType.BLOCKED,
                confidence=0.0,
                timestamp=now,
            )
        return AgentOutput(
            block_client=None,
            block_internal=(
                f"EXECUTION_FAULT: max retries ({_MAX_EXECUTION_RETRIES}) exceeded. "
                "Escalating to human."
            ),
            action=ActionType.ESCALATE_HUMAN,
            status=StatusType.FAILED,
            confidence=0.0,
            timestamp=now,
        )

    def _loop_fault(self, now: datetime, retry_count: int) -> AgentOutput:
        """LOOP_FAULT allows up to 3 iterations before hard failure."""
        if retry_count < _MAX_LOOP_ITERATIONS:
            return AgentOutput(
                block_client=None,
                block_internal=(
                    f"LOOP_FAULT: iteration {retry_count + 1}/{_MAX_LOOP_ITERATIONS}."
                ),
                action=ActionType.WAIT,
                status=StatusType.BLOCKED,
                confidence=0.0,
                timestamp=now,
            )
        return AgentOutput(
            block_client=None,
            block_internal=(
                f"LOOP_FAULT: max iterations ({_MAX_LOOP_ITERATIONS}) reached. "
                "Terminating to prevent infinite loop."
            ),
            action=ActionType.FAIL,
            status=StatusType.FAILED,
            confidence=0.0,
            timestamp=now,
        )

    def _confidence_fault(self, now: datetime) -> AgentOutput:
        """CONFIDENCE_FAULT escalates to human without retry."""
        return AgentOutput(
            block_client=None,
            block_internal=(
                "CONFIDENCE_FAULT: confidence below threshold. "
                "Escalating to human for review."
            ),
            action=ActionType.ESCALATE_HUMAN,
            status=StatusType.NEEDS_APPROVAL,
            confidence=0.0,
            timestamp=now,
        )
