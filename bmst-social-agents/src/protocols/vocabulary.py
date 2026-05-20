"""Controlled vocabulary for the AOS protocol layer.

All enums are str-based so they serialise cleanly to JSON without extra conversion.
"""

from enum import Enum


class ActionType(str, Enum):
    """What the agent wants to happen next."""

    SEND_MESSAGE = "send_message"
    REQUEST_APPROVAL = "request_approval"
    ESCALATE_HUMAN = "escalate_human"
    WAIT = "wait"
    DELEGATE_AGENT = "delegate_agent"
    COMPLETE = "complete"
    FAIL = "fail"


class StatusType(str, Enum):
    """Current state of the agent task."""

    NEEDS_APPROVAL = "needs_approval"
    TASK_COMPLETE = "task_complete"
    BLOCKED = "blocked"
    NEEDS_MORE_CONTEXT = "needs_more_context"
    FAILED = "failed"


class FaultType(str, Enum):
    """Category of fault that occurred during agent execution."""

    EXECUTION_FAULT = "execution_fault"
    SCHEMA_FAULT = "schema_fault"
    CONFIDENCE_FAULT = "confidence_fault"
    SCOPE_FAULT = "scope_fault"
    LOOP_FAULT = "loop_fault"
    SAFETY_FAULT = "safety_fault"


class Platform(str, Enum):
    """Supported social media platforms."""

    INSTAGRAM = "instagram"
    LINKEDIN = "linkedin"
    FACEBOOK = "facebook"
    TIKTOK = "tiktok"
