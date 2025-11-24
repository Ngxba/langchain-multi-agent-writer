# Phase 2 — Middleware, Safety Rails, and Agent–Tool Wiring (notebook-first)

> Goal: make the **agent core production-ready** by wiring a robust middleware stack (HITL, retries, fallback, context control, cost guards, PII), defining **approval checkpoints**, and **binding tools** to departments. You’ll be able to run end-to-end in a notebook with deterministic tests and eval hooks. No UI/backend yet.

---

## 1) Middleware Stack (order, scope, and rationale)

> Middleware runs in a predictable order. Earlier layers are more “foundational” (limits, PII), later layers are “adaptive” (summarization, fallback).

**Recommended global order (top → bottom):**

1. **Tool/Model Call Limits**

   * Enforce hard ceilings to prevent runaway loops:

     * `max_model_calls_per_run` (e.g., 30)
     * `max_tool_calls_per_run` (e.g., 50)
     * `max_depth_per_run` (e.g., 8 graph hops)
2. **PII Redaction** (egress filter)

   * Masks emails, phones, SSNs, and exact addresses before *any* text leaves the system.
3. **Human-in-the-Loop (HITL) Gate**

   * Interrupt **before** selected tool calls (see Risk Matrix below).
   * Requires explicit “approve/deny + rationale”.
4. **Tool Retry (exponential backoff)**

   * Handles transient network/API errors in tools.
5. **Model Fallback**

   * Route to a backup model on provider/model errors or rate limits.
   * Propagate a `fallback_used: bool` flag to state.
6. **Summarization / Context Manager**

   * Compress long context windows (notes/citations) while preserving anchors (`claim_id`, `source_id`).
7. **Style Profile Injector (custom)**

   * Injects the current `STYLE_PROFILE` into prompts at runtime (customizable per run).
8. **Canonical Citations (custom)**

   * Normalizes `web.fetch` outputs into `{source_id, url, title, snippet, accessed_at}` and dedupes sources.

**Why this order?**

* Limits and PII must apply to **everything**.
* HITL must see original intents **before** retries/fallback obscure root causes.
* Fallback and summarization are adaptive; place them later.
* Prompt/style and citations are last so they operate on the near-final request/response.

---

## 2) HITL Checkpoints (what pauses, what requires approval)

### 2.1 Risk Matrix → Gate Policy

| Tool / Action        |    Domain trust |      Data sensitivity | Gate?                     | Notes                                                       |
| -------------------- | --------------: | --------------------: | ------------------------- | ----------------------------------------------------------- |
| `web.fetch(url)`     | **Unknown/Low** |                   N/A | **YES**                   | Pause before fetch; require rationale.                      |
| `web.fetch(url)`     |      High/known |                   N/A | No                        | Proceed, but log.                                           |
| `web.search(query)`  |             Any |                   N/A | No                        | Search is harmless; fetch is gated.                         |
| `drawio.export(png)` |             Any |                   N/A | No                        | Safe local render; if using external renderer later → gate. |
| `plagiarism.scan`    |             Any | Draft may contain PII | **YES (if external API)** | Gate if provider sees full draft.                           |
| `publish` (Phase 5+) |             Any |         Public action | **YES**                   | Always gated, not enabled in P2–P3.                         |

**Domain Trust tiers**

* **High:** official docs, major standards bodies, established news/academic sites you whitelist.
* **Unknown/Low:** any domain not in the allow-list.

### 2.2 HITL Request Payload

```
{
  "checkpoint_id": "<uuid>",
  "agent": "Researcher",
  "tool": "web.fetch",
  "args": {"url": "http://example.com"},
  "risk": {"domain_trust": "unknown", "reason": "not-in-allowlist"},
  "state_preview": {"topic": "...", "current_sources": 4},
  "suggested_decision": "approve|deny",
  "timeout_s": 600
}
```

### 2.3 Approval Response

```
{
  "checkpoint_id": "<uuid>",
  "decision": "approve|deny",
  "rationale": "Concise reason or constraint, e.g., only fetch this path.",
  "constraints": {"max_bytes": 200000, "follow_links": false}
}
```

Approvals/denials are appended to `state.approvals[]`.

---

## 3) Tool Binding per Department (clean separation of concerns)

> Tools are bound narrowly to each agent. This keeps prompts small, reduces error surface, and simplifies audits.

### 3.1 Researcher

* **Allowed tools:**

  * `web.search({query, k})`
  * `web.fetch({url})` (**HITL gate** on unknown domains)
  * `local.search({query, top_k})`
  * `citation.builder({claims, sources})`
* **Produces:** `facts[]`, `citations[]`, `notes.json`

### 3.2 Writer

* **Allowed tools:**

  * None by default (reads `facts[]`/`citations[]`, `STYLE_PROFILE`)
  * Optional `readability.check({markdown})`
* **Produces:** `draft.md` and `draft.html`
* **Constraint:** May not call `web.fetch` (prevents unsupported research drift).

### 3.3 Editor

* **Allowed tools:**

  * `seo.readability({markdown})`
  * `plagiarism.scan({markdown})` (**HITL gate** if external)
  * Access to `citations[]` for link verification (heads only; no external fetch unless approved)
* **Produces:** updated drafts, `issues[]`, pass/fail flag

### 3.4 Diagrammer

* **Allowed tools:**

  * `drawio.generate({intent, type, nodes, edges})`
  * `drawio.export({xml, format:'png'})`
* **Produces:** `.drawio xml`, `diagram.png`, `diagram_notes`

---

## 4) Configuration (env + policy files)

Create **two small config layers** you can tweak without code:

### 4.1 `policy.yaml`

```yaml
limits:
  max_model_calls_per_run: 30
  max_tool_calls_per_run: 50
  max_depth_per_run: 8

hitl:
  gate_web_fetch_unknown_domain: true
  gate_plagiarism_external: true
  approval_timeout_s: 600
  allow_domains:
    - docs.langchain.com
    - reference.langchain.com
    - arxiv.org
    - en.wikipedia.org
    - developer.mozilla.org
  deny_domains: []   # optional denylist; deny always prompts HITL

fallback:
  primary: "openai/gpt-X"
  secondary: "anthropic/claude-Y"
  use_on_rate_limit: true
  use_on_timeout: true

summarization:
  target_context_tokens: 6000
  preserve_keys: [claim_id, source_id, url]
```

### 4.2 `style_profile.json` (example; swappable at runtime)

```json
{
  "name": "Neutral-Concise",
  "voice": "neutral, confident, helpful",
  "sentence_length": "12-20 words",
  "structure": ["hook","summary","sections","key-takeaways","CTA"],
  "do_not_use": ["sensational claims","vague sources"],
  "citation_policy": "≥2 independent sources for non-trivial claims; primary preferred"
}
```

---

## 5) Notebook Cell Structure (how to organize Phase 2 work)

1. **Imports & Keys** (models, tracing off by default)
2. **Configs** (`policy.yaml`, `style_profile.json` loaders)
3. **State Types** (shared AgentState)
4. **Middleware** (instantiate in **the order** above)
5. **Tool Adapters** (pure functions with strict schemas; stubs OK)
6. **Agent Prompts** (from Phase 1, kept in variables)
7. **Agent Nodes** (functions calling model+tools)
8. **Graph Wiring** (entry → edges → stop condition)
9. **HITL Simulators** (simple approve/deny callback)
10. **Smoke Tests** (see Section 7)

This mirrors how you’ll later split into packages; the **semantics won’t change** when you move to services.

---

## 6) Custom Middleware Specs (prompts stay code-free)

### 6.1 Style Profile Injector

**Hook:** `@dynamic_prompt`
**Input:** active `style_profile`
**Effect:** Prefix each system/task prompt with the profile; do **not** hard-code style into prompts.
**Failure mode:** If missing profile → fall back to Neutral-Concise and record `style_profile_used: default`.

### 6.2 Canonical Citations

**Hook:** `@wrap_tool_call` on `web.fetch`
**Normalization:**

```
{ source_id: sha1(url), url, title, snippet, accessed_at }
```

**Dedupe rule:** prefer first-seen per domain unless new content adds unique claim coverage.
**Propagation:** attach to `state.citations[]` and map to `facts[].source_ids`.

---

## 7) Tests & Evals (deterministic, notebook-friendly)

### 7.1 Unit Tests (quick)

* **Limits**: exceed `max_tool_calls_per_run` → run aborts with clear error.
* **HITL**: simulate unknown domain fetch → expect pause; approve → proceed; deny → tool skipped with warning.
* **PII**: draft containing email/phone → outbound text shows masked versions.
* **Fallback**: simulate model failure → expect secondary model used, `fallback_used=true`.
* **Summarization**: inject oversized `facts/citations` → verify token budget met and anchors preserved.

### 7.2 Integration Tests (end-to-end)

* **Topic**: “Kafka fundamentals” (use your uploaded doc as local context).

  * Local file path: `sandbox:/mnt/data/35958103-9e9b-4e6a-8fd6-98a5db226add.docx`
  * Expect: Researcher returns ≥2 sources per claim (mix local + web stubs), Writer produces `draft.md`, Editor flags 0 critical issues, Diagrammer outputs one PNG.

### 7.3 Eval Metrics (for LangSmith later, dry-run now)

* **Missing-citation rate** (% of non-trivial claims without ≥2 sources).
* **Style adherence** (regex/rules for structure + sentence length).
* **Reading level** (FKGL or similar) within target ±1.
* **Fallback usage rate** (should be low but non-zero in fault tests).
* **HITL approval latency** (recorded even when simulated).

**Pass criteria for Phase 2:**

* All unit tests pass.
* Integration run completes within limits and yields:

  * `draft.md`, `draft.html`, `diagram.png`, `citations[]`, `issues[]` (0 critical).
* HITL simulation behaves as expected for unknown domains.
* Fallback and summarization flags propagate in state.

---

## 8) Runbook (what to do in the notebook)

1. **Load configs** → print active limits & style.
2. **Instantiate middleware chain** (in the prescribed order).
3. **Bind tools to departments** (Researcher/Writer/Editor/Diagrammer).
4. **Create graph** with entry = Researcher; edges as Phase 1.
5. **Set stop condition**: presence of `artifacts['draft.md']` **and** Editor `pass=True`, or iteration cap.
6. **Run smoke topic**: “Kafka fundamentals”.
7. **Review state**: approvals log, citations, `fallback_used`, `summarized=true` markers.
8. **Record artifacts**: store outputs locally (same paths the future service will use).
