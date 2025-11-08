"""
Content Planner Agent for BigData Newsletter System — EIC (hybrid)
- Phase 1: human-friendly chat (ReAct), ends with `STATE JSON` fence.
- Phase 2: programmatic structured output via agent.produce_output(...)
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph_swarm import create_handoff_tool

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field

from config.settings import get_agent_config
from config.agent_names import EIC
from config.agent_handoffs import get_agent_handoffs
from prompts.agent_prompts import get_agent_prompt


# --------- Phase 2 schemas (minimal and explicit) ---------


class TargetReader(BaseModel):
    role: str = Field(..., description="Who the reader is")
    current_knowledge: str = Field(..., description="What they already know")
    primary_goal: str = Field(..., description="What they want to achieve")


class OutlineEntry(BaseModel):
    h2: str
    notes: str = ""
    visual: str = Field("none", description='one of: "none", "diagram", "table", "code"')


class DiagramOpportunity(BaseModel):
    type: str = Field(..., description='one of: "sequence", "flowchart", "architecture"')
    why: str
    placed_in: str


class ExampleItem(BaseModel):
    name: str
    what_it_shows: str


class GlossaryItem(BaseModel):
    term: str
    definition: str


class FurtherReadingItem(BaseModel):
    label: str
    hint: str


class EditorialBriefPayload(BaseModel):
    title: str
    angle: str
    target_reader: TargetReader
    reader_promise: str
    key_questions: List[str]
    must_include_points: List[str]
    must_avoid: List[str]
    outline: List[OutlineEntry]
    diagram_opportunities: List[DiagramOpportunity]
    examples: List[ExampleItem]
    glossary: List[GlossaryItem]
    further_reading: List[FurtherReadingItem]


class EICArtifactEnvelope(BaseModel):
    """Universal envelope for handoffs."""

    artifact_type: str = Field("editorial_brief", const=True)
    agent: str = Field("eic", const=True)
    version: str = Field("1.0")
    status: str = Field("complete")
    meta: Dict[str, Any] = Field(default_factory=dict)
    errors: List[str] = Field(default_factory=list)
    data: Dict[str, Any] = Field(default_factory=dict, description='Contains {"brief": EditorialBriefPayload, "acceptance_criteria": [..]}')


# The frozen state captured at the end of Phase 1
class EICState(BaseModel):
    angle: str
    target_reader: TargetReader
    reader_promise: str
    key_questions: List[str]
    must_include_points: List[str]
    must_avoid: List[str]
    outline_stub: List[str] = Field(default_factory=list)


# --------- Helpers ---------

STATE_BLOCK_PATTERN = re.compile(r"```STATE JSON\s*(\{.*?\})\s*```", re.DOTALL | re.IGNORECASE)


def _extract_state_json_from_text(text: str) -> Optional[dict]:
    """Grab the fenced STATE JSON block from a Phase 1 message."""
    m = STATE_BLOCK_PATTERN.search(text or "")
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except Exception:
        return None


# --------- Factory ---------


def create_eic_agent():
    """
    Create the EIC agent with hybrid behavior:
      - ReAct agent for Phase 1 dialogue
      - agent.produce_output(...) for Phase 2 structured artifact
    """
    config = get_agent_config("eic")

    # Core model (used for both ReAct and structured output)
    model = ChatOpenAI(model=config.get("model", "gpt-4o"), temperature=config.get("temperature", 0.5), tags=["eic"])

    # Handoff tools (only)
    tools = []
    for target_agent, description in get_agent_handoffs(EIC):
        tools.append(create_handoff_tool(agent_name=target_agent, description=description))

    # Phase 1 agent (dialogue)
    agent = create_react_agent(
        model,
        tools,
        prompt=get_agent_prompt(EIC),  # ensure your prompt instructs ending with STATE JSON
        name=EIC,
    )

    # --------- Phase 2: structured output producer ---------

    # A separate, deterministic head for JSON generation
    json_model = ChatOpenAI(
        model=config.get("model_json", config.get("model", "gpt-4o")), temperature=config.get("temperature_json", 0.2), tags=["eic", "json"]
    ).with_structured_output(EICArtifactEnvelope)

    # Prompts for Phase 2
    produce_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                (
                    "You are the Editor-in-Chief generating a final editorial brief and acceptance "
                    "criteria for downstream agents. Use ONLY the provided state_json and meta. "
                    "Be concrete, plain-language, technical-but-readable. "
                    "Return a single JSON object conforming to the target schema."
                ),
            ),
            (
                "human",
                (
                    "state_json:\n```json\n{state_json}\n```\n"
                    "meta (topic/audience/notes/checksum):\n```json\n{meta}\n```\n"
                    "Requirements:\n"
                    "- Expand outline_stub into structured outline entries with appropriate `visual` hints.\n"
                    "- Create 1-3 diagram_opportunities.\n"
                    "- Provide 2-4 concrete examples, a 5-8 term glossary, and 3-5 further reading items.\n"
                    "- Include acceptance_criteria mirroring our standard quality gates.\n"
                    "Output: JSON only."
                ),
            ),
        ]
    )

    # Optional extractor (if user didn't paste STATE JSON, we can synthesize it)
    state_extract_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "Extract a minimal, factual STATE JSON for the EIC from the following text. "
                "Do not include hidden reasoning. Return JSON only, matching the EICState schema.",
            ),
            ("human", "{message}"),
        ]
    )
    state_model = ChatOpenAI(
        model=config.get("model_state", config.get("model", "gpt-4o")), temperature=0.0, tags=["eic", "state"]
    ).with_structured_output(EICState)

    async def produce_output(
        reasoning: Optional[str] = None,
        state_json: Optional[Dict[str, Any]] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Phase 2: Turn STATE JSON into the formal EIC artifact (envelope).
        Usage:
            structured = await agent.produce_output(reasoning=msg)
        or:
            structured = await agent.produce_output(state_json=state, meta={...})
        """
        # 1) Prefer explicit state_json; else extract from the Phase 1 message
        frozen_state = state_json or _extract_state_json_from_text(reasoning or "")
        if frozen_state is None and reasoning:
            # Synthesize a minimal state from the conversation
            frozen_state = await (state_extract_prompt | state_model).ainvoke({"message": reasoning})
            frozen_state = json.loads(frozen_state.json())
        if frozen_state is None:
            raise ValueError("No STATE JSON found. Provide `state_json` or Phase-1 `reasoning` that ends with a STATE JSON fence.")

        # 2) Meta for traceability
        meta = meta or {}
        if "checksum" not in meta:
            # Simple checksum: stable JSON string length (replace with your own hash if needed)
            meta["checksum"] = len(json.dumps(frozen_state, sort_keys=True))

        # 3) Invoke deterministic JSON head
        envelope: EICArtifactEnvelope = await (produce_prompt | json_model).ainvoke(
            {"state_json": json.dumps(frozen_state, ensure_ascii=False), "meta": json.dumps(meta, ensure_ascii=False)}
        )

        # 4) Return as dict for easy handoff to next agent
        return json.loads(envelope.json())

    # attach the producer to the agent (hybrid usage)
    agent.produce_output = produce_output  # type: ignore[attr-defined]

    return agent
