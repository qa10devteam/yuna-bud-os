# spec/05 — AI layer & ingestion

## AI router (`services/ai/router.py`)

```python
def route(task: Task) -> LLMTarget:
    # high-volume / extraction / classification / OCR / pre-filter  -> local Ollama
    # hard reasoning (red-flag reasoning, axiom extraction, explanation, chat-brain) -> Bedrock Claude
```
Rules:
- **Local (Ollama):** `classify`, `extract_fields`, `ocr_vlm` (Gemma 4 12B), `prefilter_match`, `route`.
  Zero egress, zero marginal cost.
- **Cloud (Bedrock Claude, eu-central-1):** `reason_redflags`, `extract_axioms`, `explain_verdict`,
  `chat_edit`. Tiered: Haiku-class for light, Sonnet for default, Opus only if explicitly configured.
- **PII redaction** before any cloud call; **owner RMS / rate_card data is never included in any cloud prompt**
  (assert in code + test).
- **Cost controls:** prompt caching for repeated context (owner profile, document chunks); **Batch API** for
  non-interactive document analysis; per-call + per-day caps (`COST_CAPS`); refuse over cap with
  `cost_cap_exceeded`.
- Interface-driven: `LLMClient` protocol with `OllamaClient`, `BedrockClient`, and `StubClient` (CI).
- Every call logs `{task, target, model, tokens_in, tokens_out, cost, ms}` to `agent_run`/metrics.

### Prompt discipline
- All cloud prompts request **structured JSON** (Pydantic-validated) and forbid free-form decisions.
- Extraction prompts return candidates with `provenance`; anything without provenance is dropped.
- Store prompts as versioned templates under `services/ai/prompts/` (PL output where user-facing).

### Embeddings
- Local embedding model via Ollama (dim → set `document_chunk.embedding vector(N)` to match). Hybrid retrieval
  (vector + keyword) + re-rank for Agentic RAG.

## Ingestion connectors (`services/ingest/`)

Common `Connector` protocol: `fetch_since(watermark) -> list[RawNotice]`, `to_tender(raw) -> TenderUpsert`.
Abstraction + monitoring + HTML-parse fallback. Respect ToS/rate-limits. **VERIFY** all schemas at build.

| Connector | Source | Notes |
|---|---|---|
| `bzp/` | e-Zamówienia read API `${BZP_API_BASE}` (`/mo-board/api/v1/notice`) | national notices ≥130k PLN; CPV, deadlines; read access without integration procedure (VERIFY) |
| `ted/` | TED EU notices | above-EU-threshold; map TED fields → tender |
| `bk/` | Baza Konkurencyjności | EU-funded competitive-principle; public search; API surface limited (VERIFY) |
| `bip/` | municipal BIPs (dolnośląskie/śląskie/opolskie/lubuskie) | sub-130k long tail; per-BIP adapters + generic HTML parser; Tier 2+ |

- Watermark per connector persisted; ingestion idempotent (upsert on `(source,external_id)`).
- CI uses **recorded fixtures** in `tests/fixtures/notices/`; zero network. An integration suite (opt-in,
  network) hits live endpoints behind a flag.

## Document pipeline (`services/documents/`)

```
documents/
  fetch.py    # download attachments to local FS (idempotent, checksum)
  classify.py # kind = swz|design|stwior|przedmiar|other (filename + content heuristics + local LLM)
  ocr.py      # text-layer via pymupdf; scanned -> Gemma 4 12B VLM; tables -> structured extraction
  parse_przedmiar.py # -> przedmiar_item[] (position_no, knr_code?, desc, unit, quantity, page)
  parse_ath.py       # .ath / Norma XML interchange (VERIFY format)  -> przedmiar_item[]
  chunk.py    # chunk + embed -> document_chunk
```
- **Provenance everywhere:** each `przedmiar_item` and chunk carries `page`. Low-confidence OCR rows are
  flagged (`confidence<threshold`), not dropped.
- `.ath` parsing is **VERIFY** (de-facto Polish kosztorys interchange; validate against a real sample in Phase 0).

**Acceptance (ingestion+docs):** with fixtures, connectors upsert correct tenders; `analyze` produces parsed
przedmiar items with page provenance; pipeline is idempotent and runs offline in CI via stubs.
