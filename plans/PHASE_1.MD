# Phase 1 — Production-grade Agent **Design & Prompts** (notebook-first, no UI/backend)

> Goal: lock a **maintainable, modular** agent system—**state, roles, tools, guardrails, prompts, and evaluation**—that runs in a notebook now and can be lifted into services later **without changing semantics**. We will use **LangChain Agents** implemented on **LangGraph** primitives for reliability and control (stop conditions, typed state, dynamic model binding). ([docs.langchain.com][1])

---

## 1) Scope & Guarantees

**In scope now**

* Multi-agent orchestration (Researcher → Writer → Editor → Diagrammer) on LangGraph with a shared, typed **Agent State** and a clear stop condition. ([reference.langchain.com][2])
* **Tool contracts** (I/O specs) and **HITL** checkpoints using middleware hooks (approval interrupts). ([reference.langchain.com][3])
* **Production prompts** (system + tool-use prompts + checklists + self-verification rubrics) that are **style-profile aware** (customizable, not fixed).
* **Quality gates** & **evaluation plan** (LangSmith datasets, offline/online evals). ([docs.langchain.com][4])

**Out of scope (moved to Phases 5–6)**

* Client UI, backend API, auth, multi-tenant controls (kept in mind while designing contracts).

---

## 2) Architecture Decisions (ADRs)

1. **Agents on LangGraph** (not vanilla loops): we want typed state, deterministic edges, checkpointers, and dynamic model binding via graph runtime. **Why:** safer stop conditions, easier HITL, easier later deployment. ([reference.langchain.com][2])
2. **Prebuilt + custom middleware**: adopt production middleware (HITL, retry, fallback, summarization, call-limits, PII) and add two custom: *StyleProfile* (dynamic prompt injection) and *CanonicalCitations* (normalize source objects). ([reference.langchain.com][3])
3. **Context engineering per agent**: each “department” gets only the slice of state it needs; Writer never sees raw scrape noise; Editor sees draft + citations + rules; Diagrammer gets “diagram intents”. ([docs.langchain.com][5])
4. **Observability first**: every run traced; we define eval datasets and online evaluators early to avoid “prompt drift”. ([docs.langchain.com][4])

---

## 3) Shared Contracts (Notebook-ready, service-friendly)

### 3.1 Agent State (concept)

A single typed container that flows between nodes:

* `messages[]`: conversational turns (for traceability)
* `tasks[]`: structured asks (topic, brief, constraints)
* `facts[]`: normalized claims with evidence handles `{claim_id, text, source_ids[], confidence}`
* `citations[]`: canonical source objects `{source_id, url, title, snippet, accessed_at}`
* `artifacts{}`: `draft.md`, `draft.html`, `diagrams[] (png)`, `notes.json`
* `approvals[]`: HITL decisions with rationale
* `cost/tokens`: metering

This mirrors LangGraph’s stateful, stop-conditioned agent pattern; precise types help later when binding models/tools dynamically. ([reference.langchain.com][2])

### 3.2 Run Request (input to the graph)

```
{ topic, brief, requirements[], style_profile_id?, sources: [urls|files], publish=false }
```

### 3.3 Stop Conditions

* `artifacts["draft.md"]` present **AND** Editor passes all critical checks **OR** iteration cap reached. (Caps enforced via middleware.) ([reference.langchain.com][3])

---

## 4) Tools — I/O Specifications (no code, exact contracts)

> Each tool has a **strict schema** and **safety notes**; HITL can block/approve at call time via middleware interrupts. ([reference.langchain.com][3])

1. **web.search**

* **In:** `{query: str, k?: int}`
* **Out:** `[{title, url, snippet}]`
* **Notes:** prefer authority domains; log domain reputation.

2. **web.fetch**

* **In:** `{url: str}`
* **Out:** `{url, title, content, snippet, status}`
* **HITL:** required for unknown or low-trust domains before fetch (interrupt). ([reference.langchain.com][3])

3. **local.search**

* **In:** `{query: str, top_k?: int}`
* **Out:** `[{path_or_id, snippet}]`
* **Notes:** optional; mirrors future Drive/Notion adapters.

4. **citation.builder**

* **In:** `{claims: [{claim_id, text}], sources: [source_ids]}`
* **Out:** `[{claim_id, source_ids, quality_score}]`
* **Notes:** enforces ≥2 independent sources for non-trivial claims.

5. **drawio.generate**

* **In:** `{intent: str, type: enum(sequence|mindmap|swimlane|block), nodes[], edges[]}`
* **Out:** `{xml: string, preview_notes: string}`

6. **drawio.export**

* **In:** `{xml: string, format: 'png'}`
* **Out:** `{png_path_or_b64}`

7. **seo.readability**

* **In:** `{markdown: string}`
* **Out:** `{reading_level, flags[], suggestions[]}`

8. **plagiarism.scan**

* **In:** `{markdown: string}`
* **Out:** `{score, matches[]}`

> **Call-limits & retries** enforced by middleware; **fallback** models for tool-augmented calls to maintain uptime. ([docs.langchain.com][6])

---

## 5) Departments (Agents) & Context They Receive

**Researcher**

* **Gets:** `topic, brief, requirements, style constraints (read-only)`.
* **Produces:** `facts[], citations[], notes.json`.
* **Policies:** for each non-obvious claim, cite **≥2 independent** sources; track confidence; avoid tertiary summaries as single sources.

**Writer**

* **Gets:** `facts[], citations[], style_profile`.
* **Produces:** `draft.md`, `draft.html`.
* **Policies:** keep all claims anchored to `claim_id`; do not invent sources; respect structure constraints from style profile.

**Editor**

* **Gets:** `draft.*, citations[], style_profile`
* **Produces:** corrected `draft.*`, `issues[]` (rubric-tagged), pass/fail flags.
* **Policies:** enforce citation presence/quality, reading-level targets, tone, and structure.

**Diagrammer**

* **Gets:** “diagram intents” derived from outline; optional Writer hints.
* **Produces:** `.drawio xml` + `png`, referenced from draft.

Fine-grained context slicing reflects LangChain multi-agent guidance on **context engineering**. ([docs.langchain.com][5])

---

## 6) **Production Prompts** (style-customizable)

> Below are the **prompt packs** (system + task + tool-use + self-checklists). They are written to be **provider-agnostic** and **style-profile injected** at runtime via middleware `@dynamic_prompt`, per LangChain middleware docs. ([reference.langchain.com][3])

### 6.1 Global System Prompt (applies to all nodes)

```
You are part of a multi-agent newsroom. Follow the active STYLE_PROFILE (below).
Never fabricate sources or quotes. For non-trivial claims, require ≥2 independent sources.
Respect tool I/O schemas exactly. If information is missing, ask via HITL checkpoint.

STYLE_PROFILE (runtime-injected):
- voice: {voice}
- sentence_length: {sentence_length}
- structure: {structure}
- do_not_use: {do_not_use}
- citation_policy: {citation_policy}
```

### 6.2 Researcher — Task Prompt

```
Task: Build high-confidence FACTS for topic: "{topic}" within constraints: {requirements}.
Steps you MUST follow:
1) Plan queries (broad→narrow). 2) Use web.search to find sources. 3) For each promising URL, use web.fetch.
4) Extract candidate claims WITH quotes (""), page title, and URL.
5) Cross-verify each claim with ≥1 independent source. If conflict, mark low confidence.

Output:
- facts[]: [{claim_id, text, quote, source_ids[], confidence(0.0–1.0)}]
- citations[]: [{source_id, url, title, snippet, accessed_at}]
Rules:
- Prefer primary sources and official docs.
- Only include claims that have ≥2 independent sources unless labelled "background-low".
- If a tool fails or domain is unknown, trigger HITL for approval.
Self-check before returning:
- Are there at least 2 sources for each non-trivial claim?
- Are any facts extrapolations? Remove or relabel.
```

### 6.3 Writer — Task Prompt

```
Task: Draft a complete newsletter in Markdown from facts[] and STYLE_PROFILE.
Constraints:
- Preserve factual content; never invent.
- Map each paragraph to claim_ids in hidden comments <!-- claim: ... --> for traceability.
- Follow STYLE_PROFILE structure exactly; include "Key Takeaways" and optional CTA.

Output:
- draft.md (fluent markdown)
- draft.html (same content, HTML-safe)
Self-check:
- Are all non-trivial statements covered by claim_ids?
- Does the structure match STYLE_PROFILE?
- Reading flow: hook → summary → sections → takeaways → CTA.
```

### 6.4 Editor — Task Prompt (Rubric-driven)

```
Task: Enforce quality, correctness, and house style.
Checks:
- Citations: every non-trivial claim maps to ≥2 sources; links resolve; diversity of sources.
- Tone & style: matches STYLE_PROFILE (voice, sentence length, structure).
- Readability: target reading level; shorten long sentences.
- Risk: remove unverifiable or low-confidence claims; flag bias/subjectivity.

Output:
- Revised draft.md, draft.html
- issues[]: [{severity: critical|major|minor, category: citations|tone|readability|logic, msg, location}]
Pass/Fail:
- Fail if any critical issues; otherwise Pass.
```

### 6.5 Diagrammer — Task Prompt

```
Task: Translate "diagram intents" from the outline into a clear diagram.
Process:
- Choose template (sequence | mindmap | swimlane | block).
- Generate concise labels; avoid decorative clutter.
- Export PNG and reference it in draft at the appropriate section.

Output:
- drawio.xml, png
- diagram_notes: placement hints
Self-check:
- Is the diagram readable in email width (~600–700px)?
- Are labels aligned with adjacent paragraphs?
```

---

## 7) Middleware Plan (hook points & behaviors)

* **HumanInTheLoopMiddleware**
  *Interrupt before* `web.fetch` on unknown/low-trust domains; require approver note. Also gate `drawio.export` if external rendering is used later. ([reference.langchain.com][3])
* **ToolRetryMiddleware** with exponential backoff for flaky HTTP; **ModelFallbackMiddleware** to a cheaper/robust model when primary fails; **Model/ToolCallLimit** to bound cost/time; **SummarizationMiddleware** to compress context. ([docs.langchain.com][6])
* **PIIMiddleware**: redact PII before Editor returns outward artifacts. ([reference.langchain.com][3])
* **Custom: StyleProfile (@dynamic_prompt)** injects the selected profile into all agent system prompts **at runtime**—your style remains configurable, not baked in. ([reference.langchain.com][3])
* **Custom: CanonicalCitations (@wrap_tool_call)** normalizes `web.fetch` outputs into `{source_id, url, title, snippet}` and de-dups domains for diversity scoring. ([docs.langchain.com][7])

---

## 8) Evaluation & Definition of Done

**Datasets (LangSmith)**

* *Seed set*: 10–20 topics typical for your newsletter; for each topic define: brief, constraints, success examples.
* *Golden checks*: minimum citation density, independence of sources, diagram inclusion when requested, reading level target.
* *Online evaluators*: monitor production traces for missing citations %, reading-level drift, and re-edit rate. ([docs.langchain.com][4])

**Rubrics (used by Editor & evals)**

* **Citations:** ≥2 independent sources per claim (or explicitly marked **background-low**).
* **Factuality:** no contradictions between sources; uncertainty called out.
* **Style adherence:** structure and tone exactly match the active style profile.
* **Readability:** target grade (you’ll specify later), sentence length checks.
* **Diagram quality:** legibility at email width; labels map to text.

**Definition of Done (Phase 1)**

* Prompt packs finalized (Global + Researcher + Writer + Editor + Diagrammer).
* Tool I/O schemas and HITL criteria documented and stable.
* Middleware plan (built-in + custom) approved.
* Eval plan set up in LangSmith (datasets & metrics described), ready to run from a notebook. ([docs.langchain.com][8])

---

## 9) Hand-off Notes for Phase 2–3 (no action now, just foresight)

* Bind prompts and tools into a LangGraph graph with typed state and stop conditions; attach middleware stack exactly as above. ([reference.langchain.com][2])
* Keep **context slicing** strict per agent for reliability and cost—this is where most multi-agent wins come from. ([docs.langchain.com][5])

[1]: https://docs.langchain.com/oss/python/langchain/agents?utm_source=chatgpt.com "Agents - Docs by LangChain"
[2]: https://reference.langchain.com/python/langgraph/agents/?utm_source=chatgpt.com "Agents (LangGraph) | LangChain Reference"
[3]: https://reference.langchain.com/python/langchain/middleware/?utm_source=chatgpt.com "Middleware | LangChain Reference"
[4]: https://docs.langchain.com/langsmith/evaluation?utm_source=chatgpt.com "LangSmith Evaluations - Docs by LangChain"
[5]: https://docs.langchain.com/oss/python/langchain/multi-agent?utm_source=chatgpt.com "Multi-agent - Docs by LangChain"
[6]: https://docs.langchain.com/oss/python/langchain/middleware/built-in?utm_source=chatgpt.com "Built-in middleware - Docs by LangChain"
[7]: https://docs.langchain.com/oss/python/langchain/middleware/custom?utm_source=chatgpt.com "Custom middleware - Docs by LangChain"
[8]: https://docs.langchain.com/langsmith/evaluation-concepts?utm_source=chatgpt.com "Evaluation Concepts - Docs by LangChain"
[9]: https://docs.langchain.com/langsmith?utm_source=chatgpt.com "LangSmith docs - Docs by LangChain"
