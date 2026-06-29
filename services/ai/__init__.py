"""services/ai — LLM router and clients (spec/05).

Routes tasks to appropriate backend:
  - Local (Ollama/stub): classify, extract_fields, ocr_vlm, prefilter_match
  - Cloud (stub in M2): reason_redflags, extract_axioms, explain_verdict, chat_edit
"""
from .router import route, LLMTarget, Task
from .clients import LLMClient, StubClient

__all__ = ["route", "LLMTarget", "Task", "LLMClient", "StubClient"]
