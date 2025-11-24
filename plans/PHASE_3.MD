# Phase 3 — Multi-Agent Execution Order, Self-Verification Rubrics, and Test Matrix (notebook-first)

> Goal: lock the **execution flow**, **quality gates**, and **rubrics** so the system is production-ready from a notebook—before any UI/backend. We’ll pin how agents hand off, what each one must prove before passing control, how tools are routed, and how we evaluate runs (offline now, online later via LangSmith). Guidance is aligned with LangChain Agents, LangGraph orchestration (typed state, dynamic model binding), multi-agent context engineering, and Middleware (built-ins + custom). ([LangChain Docs][1])

---

## 1) Execution Graph (deterministic, stop-conditioned)

**Entry → Researcher → Writer → Editor → Diagrammer → Finalize (END)**

* **Entry**: Validate `RunRequest` and load `STYLE_PROFILE`.
* **Researcher**: build `facts[]` + `citations[]`; must satisfy rubric (below).
* **Writer**: transform `facts[]` into `draft.md/html`, preserving claim anchors.
* **Editor**: enforce correctness, style, readability; returns Pass/Fail and `issues[]`.
* **Diagrammer**: generate `.drawio+xml` + `png` for any “diagram intents” identified by Writer/Editor.
* **Finalize**: stop if Editor Pass **and** `draft.md` present **and** any required diagrams present; else loop back to the failing node (max N loops set in limits).
  This pattern mirrors LangGraph’s stateful agents with explicit edges & stop conditions; dynamic model binding remains available if we later route by topic/length (ensure `.bind_tools()` invariants). ([LangChain Docs][2])

---

## 2) Context Slicing (who sees what, and why)

* **Researcher sees:** `{topic, brief, requirements}` and **minimal** prior artifacts; not the draft.
* **Writer sees:** `facts[], citations[], STYLE_PROFILE`, not raw scrape content.
* **Editor sees:** `draft.*, citations[], STYLE_PROFILE`, limited prior messages.
* **Diagrammer sees:** “diagram intents” (from outline/Editor), relevant section text only.
  Fine-grained “context engineering” reduces hallucinations and cost; it’s the core of multi-agent quality. ([LangChain Docs][3])

---

## 3) Tool Routing (strict, per agent)

(From Phase 2; reaffirmed here since it affects rubrics)

* **Researcher**: `web.search`, `web.fetch` (HITL for unknown domains), `local.search`, `citation.builder`.
* **Writer**: no web tools; optional `readability.check`.
* **Editor**: `seo.readability`, `plagiarism.scan` (HITL if external provider).
* **Diagrammer**: `drawio.generate`, `drawio.export('png')`.
  Global call limits, retries, fallback, PII, summarization, and style-injection apply via middleware in a defined order. ([LangChain Docs][4])

---

## 4) Self-Verification Rubrics (per agent, objective & auditable)

### 4.1 Researcher — **Evidence Integrity rubric**

**Must Pass All**

* **Independence:** Each **non-trivial** claim has **≥2 independent** sources (unique domains).
* **Source Quality:** Prefer primary/official sources; if secondary used, label as such.
* **Traceability:** Each claim has `{claim_id, text, quote, source_ids[], confidence}`; quotes are exact.
* **Coverage:** The brief’s explicit requirements are addressed (mark unmet as TODO).
* **Risk:** Any unknown/low-trust domain access required HITL approval and appears in `approvals[]`.
  If a criterion fails, the Researcher must re-search/refine before yielding. (Middleware enforces iteration caps.) ([LangChain Docs][1])

### 4.2 Writer — **Fidelity & Structure rubric**

**Must Pass All**

* **Fidelity:** Every non-trivial statement maps to 1+ `claim_id` (hidden HTML/MD comments like `<!-- claim: abc123 -->`).
* **No Fabrication:** No new facts or inferred numbers; if context missing, request loop back to Researcher.
* **Structure:** Matches `STYLE_PROFILE.structure` exactly (hook → summary → sections → key takeaways → CTA).
* **Clarity:** Sentences within target length range; passive voice minimized per style profile.
* **Link Stubs:** In-text links reference canonical `citations[]` by `source_id`.
  Failing items bounce to Writer again; do not pass downstream with known fidelity gaps.

### 4.3 Editor — **Correctness & Readability rubric**

**Critical (any fails → Fail overall)**

* **Citation sufficiency:** Each non-trivial claim has ≥2 independent sources, links resolve, domains diversified.
* **Contradictions:** No internal or cross-source contradictions; uncertain items labeled or removed.
* **PII & Safety:** No leaked PII; no unannotated risky advice.
  **Major (all must be resolved or waived via HITL):**
* **Style adherence:** Matches `STYLE_PROFILE.voice/structure/sentence length`.
* **Reading level:** Within target ±1 grade (FKGL or similar).
  **Minor (should fix, can pass if documented):**
* Typos, micro-flow issues, light tone tweaks.
  The Editor records `issues[] = [{severity, category, msg, location}]` and sets Pass/Fail.

### 4.4 Diagrammer — **Legibility & Relevance rubric**

* Diagrams must be readable at ~650px width, labels concise, and placed near referencing paragraph.
* Export both `.drawio` and `png`; file names stable for later publishing.

---

## 5) Failure Modes & Recovery Rules

* **Missing evidence:** Researcher loops (max K) with new queries; if still missing, explicitly mark “background-low” claims or drop.
* **HITL deny:** Replace/skip that URL/tool call; log denial, continue if possible.
* **Rate limits or model errors:** Fallback model engaged; record `fallback_used=true`.
* **Token overflows:** Summarization middleware compresses notes/citations while preserving `{claim_id, source_id}` anchors.
  All are standard capabilities in the Agents + Middleware + LangGraph stack. ([LangChain Docs][1])

---

## 6) Evaluation Plan (offline now; online later)

### 6.1 Datasets (seed, 15–25 items)

* Topics typical of your newsletter. Include 3–5 that **require diagrams**.
* Include 2–3 adversarial prompts (ambiguous, numerically tricky, or volatile facts).
* Include at least one topic that leverages your local sample:

  * `sandbox:/mnt/data/35958103-9e9b-4e6a-8fd6-98a5db226add.docx` (used as a local source path).

### 6.2 Evaluators & Metrics

* **Citation sufficiency**: % of non-trivial claims with ≥2 independent sources.
* **Source diversity**: domain entropy per article.
* **Style adherence**: regex/heuristics for structure, sentence length.
* **Readability**: FKGL within target ±1.
* **HITL utilization/latency**: approvals for unknown domains; time to approve.
* **Fallback usage**: % runs using secondary model (should be low but non-zero in stress tests).
* **Diagram inclusion**: for topics tagged “diagram-required”.
  Set up now; wire to **LangSmith** once keys are available for UI dashboards & online evaluators. ([LangChain Docs][5])

---

## 7) Compact Test Matrix (run in notebook; no UI required)

| ID  | Scenario                  | Expectation                                      | Pass Criteria                             |
| --- | ------------------------- | ------------------------------------------------ | ----------------------------------------- |
| T1  | Happy path, general topic | Draft + citations + 0 critical issues            | Editor Pass; ≥2 sources/claim             |
| T2  | Unknown domain fetch      | HITL interrupt then approve                      | Approval logged; fetch proceeds           |
| T3  | HITL deny                 | Alternate source used                            | Denial recorded; still Pass               |
| T4  | Evidence missing          | Researcher loops up to K; marks “background-low” | No uncited claims remain                  |
| T5  | Long notes (token stress) | Summarization kicks in                           | Anchors `{claim_id, source_id}` preserved |
| T6  | Model failure             | Fallback engaged                                 | `fallback_used=true`, run completes       |
| T7  | External plagiarism scan  | HITL gate before sending draft                   | Approval enforced                         |
| T8  | Style enforcement         | Wrong structure                                  | Editor returns Major issues; loop back    |
| T9  | Diagram required          | PNG + .drawio generated & referenced             | Image legible at 650px                    |
| T10 | Local doc as source       | Local search hit appears as citation             | `citations[]` includes local path         |

---

## 8) Prompts: Phase-3 refinements (provider-agnostic, style-injectable)

> These are deltas on Phase-1 prompts to make them **self-policing**. The active `STYLE_PROFILE` is injected at runtime via middleware `@dynamic_prompt`. ([LangChain Docs][6])

### 8.1 Researcher — Add “Independence Test”

Append to instructions:

```
For every non-trivial claim:
- Independence Test: Verify sources are from different root domains and don’t quote each other verbatim.
- If only one solid source exists, label the claim "background-low" and propose a reframe for the Writer that avoids hard assertions.
Return a coverage table: requirement → evidence status [met | partial | missing].
```

### 8.2 Writer — Enforce Claim Anchors

Append to instructions:

```
Every paragraph containing non-trivial claims must include hidden anchors mapping to claim_ids:
<!-- claims: id1,id2 -->
If a section lacks adequate claims, output a TODO comment requesting Researcher follow-up instead of speculating.
```

### 8.3 Editor — Add Contradiction & Diversity Checks

Append to instructions:

```
Run contradiction scan: flag any statements that conflict with source text or with other statements.
Compute domain diversity: if >60% of claims rely on a single domain, return Major issue "low diversity".
```

### 8.4 Diagrammer — Placement Contract

Append to instructions:

```
Add a "diagram_notes" block listing the exact section header and one-sentence rationale. Ensure filenames are stable for future publishing pipelines.
```

---

## 9) Governance & Auditability

* **Approvals & denials** are immutable records in `approvals[]` with timestamps + rationale.
* **Citations** normalized (canonical format) for audit & later link checking.
* **Model & tool counts** recorded per run to enforce budgets (limits middleware).
* **Prompt versions**: keep a `prompt_version` tag in state so we can compare evals across iterations.
  All map cleanly to LangSmith’s dataset and experiment model. ([LangChain Docs][7])

---

## 10) Definition of Done (Phase 3)

* Execution order and edges fixed; stop conditions implemented. ([LangChain Docs][2])
* Context slices per agent documented and respected. ([LangChain Docs][3])
* Self-verification rubrics finalized; Editor Pass/Fail rules locked.
* Test matrix green on notebook runs (including local-doc scenario: `sandbox:/mnt/data/35958103-9e9b-4e6a-8fd6-98a5db226add.docx`).
* Offline eval datasets & metrics prepared; ready to flip on LangSmith for dashboards when keys arrive. ([LangChain Docs][5])

[1]: https://docs.langchain.com/oss/python/langchain/agents?utm_source=chatgpt.com "Agents - Docs by LangChain"
[2]: https://docs.langchain.com/oss/python/langgraph/workflows-agents?utm_source=chatgpt.com "Workflows and agents - Docs by LangChain"
[3]: https://docs.langchain.com/oss/python/langchain/multi-agent?utm_source=chatgpt.com "Multi-agent - Docs by LangChain"
[4]: https://docs.langchain.com/oss/python/langchain/middleware/built-in?utm_source=chatgpt.com "Built-in middleware - Docs by LangChain"
[5]: https://docs.langchain.com/langsmith/evaluation?utm_source=chatgpt.com "LangSmith Evaluations - Docs by LangChain"
[6]: https://docs.langchain.com/oss/python/langchain/middleware/overview?utm_source=chatgpt.com "Overview - Docs by LangChain"
[7]: https://docs.langchain.com/langsmith?utm_source=chatgpt.com "LangSmith docs - Docs by LangChain"
