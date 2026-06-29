"""AI Router — routes tasks to local or cloud LLM target."""
from __future__ import annotations

from enum import Enum
from typing import NamedTuple


class LLMTarget(str, Enum):
    LOCAL = "local"      # Ollama / StubClient
    CLOUD = "cloud"      # Bedrock Claude / StubClient


class Task(str, Enum):
    CLASSIFY = "classify"
    EXTRACT_FIELDS = "extract_fields"
    OCR_VLM = "ocr_vlm"
    PREFILTER_MATCH = "prefilter_match"
    REASON_REDFLAGS = "reason_redflags"
    EXTRACT_AXIOMS = "extract_axioms"
    EXPLAIN_VERDICT = "explain_verdict"
    CHAT_EDIT = "chat_edit"
    SUMMARIZE = "summarize"
    EMBED = "embed"


# Tasks that run locally (zero egress, zero marginal cost)
_LOCAL_TASKS = {
    Task.CLASSIFY,
    Task.EXTRACT_FIELDS,
    Task.OCR_VLM,
    Task.PREFILTER_MATCH,
    Task.EMBED,
}

# Tasks that require cloud reasoning
_CLOUD_TASKS = {
    Task.REASON_REDFLAGS,
    Task.EXTRACT_AXIOMS,
    Task.EXPLAIN_VERDICT,
    Task.CHAT_EDIT,
    Task.SUMMARIZE,
}


def route(task: Task) -> LLMTarget:
    """Route a task to the appropriate LLM target."""
    if task in _LOCAL_TASKS:
        return LLMTarget.LOCAL
    if task in _CLOUD_TASKS:
        return LLMTarget.CLOUD
    # Default: local
    return LLMTarget.LOCAL
