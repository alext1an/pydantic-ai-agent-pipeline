# Agent Specification: Writing Assistant (Stage 1)

**Status:** Specification for a production-grade Stage 1 build
**Last updated:** 2026-09-05
**Companion documents:**

- [architecture.md](./architecture.md) — the *runtime* architecture (how PydanticAI executes the agent, the in-process FastMCP tool server, dependency boundaries).
- [agent-loop.md](./agent-loop.md) — how the PydanticAI runtime executes one run.
- [decisions.md](./decisions.md) — the design decisions and pitfalls behind the current code.

This document is the *product and contract* layer: what the agent does, its tool contracts, its output contract, and its acceptance criteria. It does not replace `architecture.md`; the two describe different layers and reference each other.

---

## Part 0 — Scope

### 0.1 What this is

A writing assistant that answers questions and drafts text **grounded in the user's own material**: local documents on disk and a company knowledge base. Every factual claim in the answer must be traceable to a source the tools actually returned.

The distinguishing goal is not fluency — the LLM already provides that. It is **grounding**: the agent must not answer from parametric memory when the question is about the user's documents or policies. If the tools return nothing relevant, the agent must say so rather than guess.

### 0.2 Stage boundary (why this is still Stage 1)

This spec deliberately stays inside the Stage 1 boundary defined in `architecture.md`:

- The tool server is **owned by this project** and runs **in-process** (`tools/mcp_server/`), not as a separately deployed service.
- The vector store is **embedded** (`sqlite-vec`), sharing one SQLite file with the relational data. No separate vector-DB process.
- No FastAPI exposure, no cross-harness platform layer. Those are Stage 2.

"Production-grade" here means the *agent* is complete and hardened — real retrieval, enforced citations, path security, structured errors, usage limits, observability, and a real acceptance suite — not that it is deployed as distributed infrastructure. The upgrade over the original Stage 1 sketch is scope and rigor, not a change of deployment model.

Where this spec upgrades an earlier decision, it is called out explicitly (see §6).

### 0.3 Feasibility

| Belongs in the agent | Does not |
|---|---|
| Grounded Q&A over documents + KB (needs retrieval + reasoning + citation) | Deterministic format conversion (`.docx`→`.pdf`) — use a script |
| Synthesis across a file and the KB, flagging conflicts | Bulk find/replace with a fixed rule — use `sed`/a linter |

If the task is fully deterministic, it should not be an agent. The agent earns its place only where contextual retrieval and reasoning are required.

---

## Part 1 — Capabilities

Each capability has a trigger, an execution outline, and a hard boundary. Boundaries that concern safety or limits are enforced in code or by the tool server, **not** requested via the prompt (see §3.3).

| Capability | Trigger | Execution outline | Boundary |
|---|---|---|---|
| **File read** | User references a local document | `read_local_file` → returns an excerpt + metadata | Path confined to configured root; text extensions only; line-capped |
| **Knowledge retrieval** | Question about facts / policy / domain | `search_knowledge_base` → top-k chunks + source citations | Each result carries `source_document` + `section`; empty result is an allowed, explicit outcome |
| **Synthesis** | Request combining a file and the KB | Call tools (possibly across separate model steps), cross-check, answer only from returned material | Every claim cited; conflicts flagged, not silently merged |
| **Refusal / fallback** | Tools return nothing relevant, or a tool fails | Return a structured answer with `unsupported=true` and an actionable next step | Never fabricate a source or a fact |

### 1.1 Control flow

The agent runs the standard PydanticAI model/tool loop (see `agent-loop.md`); the model decides which tools to call and when to stop. Application code does **not** hard-code a fixed ReAct script in the prompt to enforce limits — the ceiling on tool calls and tokens is a runtime `UsageLimits` budget (§3.3), because a prompt instruction is advisory and a budget is enforced.

---

## Part 2 — Output Contract

**This is the central upgrade over the earlier Stage 1 design.** The executor's `output_type` changes from free-text `str` to a structured, citation-bearing model, so that "every claim is cited" is guaranteed by the schema rather than requested of the model.

```python
from pydantic import BaseModel, Field

class Citation(BaseModel):
    source_id: str                      # "KB-2024-001" or "./docs/style_guide.md"
    section: str | None = None          # "§3.2" for KB chunks
    lines: tuple[int, int] | None = None  # (1, 100) for file excerpts

class AssistantAnswer(BaseModel):
    content: str                        # the answer text shown to the user
    citations: list[Citation] = Field(default_factory=list)
    unsupported: bool = False           # true when no grounding was found

    # Contract, enforced by an output validator (see below):
    #   unsupported is False  ⇒  citations must be non-empty
    #   unsupported is True   ⇒  content is the standard "cannot answer" message
    #                            and citations is empty
```

The `unsupported ⇔ citations` invariant is enforced with a PydanticAI **output validator**. If the model returns `unsupported=false` with no citations, validation fails and the framework returns a retry prompt to the model within the retry budget — the same mechanism `agent-loop.md` §6.4 describes for tool-argument validation, reused for output. This is what makes grounding a property of the run, not a hope.

The application may wrap `AssistantAnswer` with run metadata (request id, prompt version, usage) exactly as `architecture.md` §10 describes; that wrapper is application metadata, not part of the model's output contract.

---

## Part 3 — Constraints

### 3.1 Security

- **Path confinement.** `read_local_file` resolves the requested path against a configured root (default `./docs/`) and rejects anything that escapes it. Rejection is based on the **resolved, canonical** path (after following symlinks and normalizing `..`), not on string matching of `..`, because string blocklists are bypassable (`....//`, encoded separators, symlinks). See §4.1.
- **Extension allowlist.** Only `.txt` / `.md` (configurable). Everything else is `FILE_NOT_FOUND`.
- **PII redaction — scoped precisely.** Redaction applies to **model-generated answer text** and to **KB chunks surfaced to the user**, using a documented detector (email, phone, etc.), producing tokens like `[REDACTED_EMAIL]`. It does **not** silently rewrite the bytes of a file the user explicitly asked to read; if a requested file contains PII, the excerpt is returned but the event is flagged in metadata. Redacting content the user directly requested would corrupt the very thing they asked for. This split is a deliberate decision, not an oversight.

### 3.2 Grounding and accuracy

- **Empty KB.** If retrieval returns nothing relevant, the answer is `AssistantAnswer(unsupported=true, content="No relevant sources found in the knowledge base; I can't answer this from internal knowledge.")`.
- **Conflicts.** When a local file and the KB disagree, the KB is treated as authoritative and the discrepancy is surfaced in the answer, not silently resolved.
- **No uncited claims.** Guaranteed structurally by Part 2, not by prompt wording.

### 3.3 Limits (enforced, not requested)

| Limit | Mechanism |
|---|---|
| Max tool calls / model requests per run | PydanticAI `UsageLimits` |
| Max tokens per run | `UsageLimits` |
| Tool retry budget | Agent `retries` / per-tool retry metadata |
| Per-tool timeout | Agent `tool_timeout` |
| File excerpt size | `max_lines` in the tool contract (§4.1) |

Nothing in this table is enforced by asking the model nicely in the system prompt. Each is a runtime control, consistent with `agent-loop.md`.

### 3.4 Performance targets (illustrative, to be measured)

These are initial **targets** to validate under load, not measured facts. They must be replaced with real p95 numbers from the load test before any are quoted elsewhere.

| Operation | Target p95 |
|---|---|
| `read_local_file` | ≤ 500 ms |
| `search_knowledge_base` | ≤ 200 ms |
| Full synthesis run | ≤ ~1 s + model latency |

---

## Part 4 — Tool Layer (in-process FastMCP)

Both tools are registered on the project's own `FastMCP` instance (`tools/mcp_server/server.py`) and exposed to the agent through `pydantic_ai.capabilities.MCP(local=server)` as described in `architecture.md` §6. The schemas below are the contract the model sees and the acceptance suite tests.

### 4.1 `read_local_file`

```yaml
name: read_local_file
description: "Read text from an authorized local file. Confines paths to the configured root and caps output size."
parameters:
  file_path:
    type: string
    required: true
    constraints:
      - Resolved (canonical) path must stay under the configured root (default ./docs/)
      - Extension must be in the allowlist (.txt, .md)
  max_lines:
    type: integer
    default: 100
    constraints: [1, 1000]
returns:
  content: string          # excerpt, truncated to max_lines
  metadata:
    source_path: string
    lines_read: integer
    truncated: boolean
    pii_flagged: boolean   # true if PII was detected in the excerpt (not rewritten)
errors:
  FILE_NOT_FOUND:    "File does not exist under the root, or extension not allowed"
  PERMISSION_DENIED: "Resolved path escapes the configured root"
  FILE_TOO_LARGE:    "Request exceeds max_lines bound"
```

Errors are returned as structured tool errors (machine-readable code + message), never raised as raw exceptions — consistent with `architecture.md` §9. `metadata.source_path` is what a `Citation.source_id` for a file points at.

### 4.2 `search_knowledge_base`

Backed by an **embedded** `sqlite-vec` index (a `vec0` virtual table in the same SQLite file used by the relational tools). Embeddings are stored as `float32` BLOBs; retrieval is a KNN query (`MATCH '[...]'` with a `k` parameter), optionally filtered on metadata columns.

```yaml
name: search_knowledge_base
description: "Retrieve the top-k most relevant knowledge-base chunks for a query, with source citations."
parameters:
  query:
    type: string
    required: true
  top_k:
    type: integer
    default: 3
    constraints: [1, 5]
returns:
  results:
    - content: string
      source_document: string   # "KB-2024-001"
      section: string           # "§4.3"
      relevance_score: float     # 0.0-1.0, derived from vector distance
errors:
  INDEX_UNAVAILABLE: "Vector index not loaded or sqlite-vec extension unavailable"
  NO_RESULTS:        "No chunk cleared the relevance threshold"
```

`NO_RESULTS` is a normal outcome that drives the `unsupported=true` answer path, not a failure. `source_document` + `section` populate `Citation` fields.

**Platform note (macOS).** `sqlite-vec` loads as a SQLite extension. The Python bundled with macOS disables `enable_load_extension`, so the project must run under Homebrew Python (or an equivalent build). This is an environment gate for local development on this machine and is recorded as an implementation prerequisite, not a runtime feature.

### 4.3 Indexing pipeline

The KB index must be built before search works. For Stage 1 this is an offline script that reads source documents, chunks them, embeds each chunk, and inserts `(content, source_document, section, embedding)` rows into the `vec0` table. The embedding model choice is an open question (§7). Re-indexing is a full rebuild in Stage 1; incremental sync is a Stage 2 concern.

---

## Part 5 — Acceptance Criteria

### 5.1 Functional (Given / When / Then)

| Scenario | Given | When | Then |
|---|---|---|---|
| File read (valid) | `./docs/style_guide.md` exists | "Read style_guide.md" | Returns lines 1–100 with `metadata.source_path=./docs/style_guide.md`; answer cites that file |
| File read (traversal) | root = `./docs` | "Open ../secret.txt" | Tool returns `PERMISSION_DENIED`; no file outside root is read |
| KB query (factual) | KB has "Product A latency: 5 ms" in KB-2024-005 §2.1 | "What is Product A's latency?" | `content` states 5 ms; `citations` contains `{source_id: KB-2024-005, section: §2.1}` |
| Combined synthesis | `./docs/guide.md` + a relevant KB entry exist | "Using guide.md, summarize the KB on compliance" | Answer synthesizes both; `citations` includes both the file and the KB chunk |
| No grounding | Query outside KB and file scope | "What is the capital of Mars?" | `unsupported=true`; standard cannot-answer message; empty `citations` |
| Conflict | File and KB disagree on a value | Query touching that value | Answer flags the discrepancy and prefers the KB source |

### 5.2 Non-functional

| Category | Requirement | Verification |
|---|---|---|
| Security | Path-confinement holds on a suite of malicious inputs (`../`, `....//`, absolute paths, symlink escapes, encoded separators) | Dedicated security test set; 100% rejection |
| Grounding | On a fixed factual validation set: citation coverage (share of factual claims carrying a citation) ≥ target, and citation correctness (cited source actually supports the claim) ≥ target, by human review | Validation set + human review — see note below |
| Performance | Full-run p95 within §3.4 targets once measured | Load test; record actual p95 |
| Reliability | Tool success rate ≥ target excluding user errors | Error monitoring over a run window |

**On "hallucination".** This spec does **not** claim a 0% hallucination rate; that is not verifiable or achievable for an LLM system and would be a permanently-failing gate. Grounding is instead measured as *citation coverage* and *citation correctness* on a fixed set with human review. Targets are set once a baseline exists, then defended against regression — which is exactly the "offline score ≠ production-ready" discipline this project is built to demonstrate.

---

## Part 6 — Changes vs. the earlier Stage 1 design

Recorded explicitly so `architecture.md` and this spec stay honest with each other:

1. **RAG moves into Stage 1.** `architecture.md` originally listed RAG as a non-goal with keyword-only search. This spec upgrades search to embedded semantic retrieval via `sqlite-vec`. Milvus / a standalone vector service remains Stage 2. *(architecture.md updated accordingly.)*
2. **Output contract becomes structured.** `output_type` changes from `str` to `AssistantAnswer` with enforced citations. *(architecture.md §10 updated.)*
3. **In-process boundary reaffirmed.** The original writing-assistant draft implied a containerized MCP server + Milvus (a Stage 2 deployment model). This spec pulls both back in-process/embedded to stay within Stage 1.

Unchanged from `architecture.md`: agent lives in `agents/`, not `SingleRun`; MCP integrated via `capabilities=[mcp]`; framework-private types stay out of application imports; Phoenix-managed system prompt with local fallback.

---

## Part 7 — Roadmap and Open Questions

### 7.1 Release phases

| Version | Scope | Definition of Done |
|---|---|---|
| MVP | `read_local_file` + `search_knowledge_base`; structured cited output; path security; empty-KB refusal | All §5.1 scenarios pass under `TestModel` where possible + a small live-model set; grounding baseline recorded |
| v1.0 | Synthesis + conflict flagging | Combined file+KB scenarios pass; grounding targets met on the validation set |
| v2.0 (Stage-1 ceiling) | User preferences, multi-file context, more extensions | Preferences honored; `.docx`/`.pdf` extraction — still in-process |

Deployment as a networked/containerized service, cross-harness exposure, and a standalone vector DB are **Stage 2**, not on this roadmap.

### 7.2 Open questions

1. Which embedding model backs `sqlite-vec`, and does it run locally or call a provider? (Affects latency targets and offline capability.)
2. Chunking strategy and the relevance threshold that separates a real hit from `NO_RESULTS`.
3. Where do `KB-YYYY-NNN` document IDs and `§` section labels come from — authored metadata, or derived at index time?
4. PII detector: which library/patterns, and its false-positive tolerance on technical text.
5. What is the configured file root and extension allowlist in each environment?
6. Grounding target numbers for §5.2 (set from the first baseline, not guessed up front).
