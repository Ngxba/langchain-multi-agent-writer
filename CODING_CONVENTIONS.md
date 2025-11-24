# Coding Conventions & Methodology

This document outlines the coding conventions, patterns, and methodology used in this multi-agent newsletter generation system. All contributors and AI agents should follow these guidelines to maintain consistency.

---

## Table of Contents

1. [Project Structure](#project-structure)
2. [Python Standards](#python-standards)
3. [Architecture Patterns](#architecture-patterns)
4. [Configuration Philosophy](#configuration-philosophy)
5. [Middleware Pattern](#middleware-pattern)
6. [Agent Node Pattern](#agent-node-pattern)
7. [State Management](#state-management)
8. [Tool System](#tool-system)
9. [Error Handling](#error-handling)
10. [Logging Conventions](#logging-conventions)
11. [Testing Guidelines](#testing-guidelines)
12. [Documentation Standards](#documentation-standards)
13. [File Naming Conventions](#file-naming-conventions)
14. [Import Organization](#import-organization)

---

## Project Structure

```
langchain-multi-agent-writer/
├── agents/                 # Agent implementations
│   ├── nodes/             # LangGraph node implementations
│   │   ├── base_node.py   # Abstract base class
│   │   ├── researcher_node.py
│   │   ├── writer_node.py
│   │   ├── editor_node.py
│   │   └── diagrammer_node.py
│   ├── tool_binder.py     # Tool access control
│   └── agent_factory.py   # Agent creation factory
├── config/                 # Configuration files
│   ├── agents.yaml        # Agent definitions (SINGLE SOURCE OF TRUTH)
│   ├── policy.yaml        # Middleware & safety policies
│   ├── settings.py        # Application settings
│   └── style_profiles/    # Style profile JSON files
├── middleware/            # Middleware stack
│   ├── chain.py          # Chain orchestrator
│   ├── handlers/         # Individual handlers
│   └── hitl_simulator.py # Human-in-the-loop simulator
├── prompts/               # Agent prompt templates (YAML)
├── tools/                 # Tool implementations
│   ├── adapters.py       # Tool adapter functions
│   └── web_search.py     # Tavily integration
├── workflows/             # LangGraph workflows
│   └── newsletter_graph.py
├── tests/                 # Test suites
│   ├── unit/
│   └── integration/
└── notebooks/             # Jupyter demos
```

---

## Python Standards

### Version & Dependencies

- **Python**: 3.13+ (required)
- **Package Manager**: `uv`
- **Dependency Management**: `pyproject.toml`

### Formatting Rules

| Tool | Setting |
|------|---------|
| **Line Length** | 150 characters (Black, Ruff, Flake8) |
| **Indentation** | 4 spaces (standard Python) |
| **Quotes** | Double quotes for strings |
| **Trailing Commas** | Yes, in multi-line structures |

### Type Hints

**Always use type hints** for function signatures and class attributes:

```python
# Good
def process_state(state: dict[str, Any], agent_name: str) -> dict[str, Any]:
    ...

# Good - dataclass with typed fields
@dataclass
class NodeResult:
    success: bool
    agent_name: str
    output: dict[str, Any] = field(default_factory=dict)
    next_agent: Optional[str] = None

# Avoid
def process_state(state, agent_name):  # Missing types
    ...
```

### Modern Python Features

Use Python 3.10+ features:

```python
# Type unions (3.10+)
def method(value: str | int) -> str | None:
    ...

# Instead of
from typing import Union, Optional
def method(value: Union[str, int]) -> Optional[str]:
    ...

# Match statements (3.10+)
match status:
    case "pending": handle_pending()
    case "complete": handle_complete()
    case _: handle_unknown()
```

---

## Architecture Patterns

### 1. Configuration-Driven Design

**Principle**: Configuration in YAML, behavior in Python.

```yaml
# config/agents.yaml - SINGLE SOURCE OF TRUTH
researcher:
  name: researcher
  model: gpt-4o
  temperature: 0.5
  description: "Gathers facts and citations"
  tools:
    - web.search
    - web.fetch
  handoffs:
    - to: writer
      when: "Research complete"
  prompt_file: researcher.yaml
  tags:
    - researcher
```

### 2. Factory Pattern for Agents

Agents are created through factories, not direct instantiation:

```python
# Good - Use factory
from agents.agent_factory import create_agent
agent = create_agent("researcher", tools=[search_web])

# Avoid - Direct instantiation with hardcoded values
agent = ChatOpenAI(model="gpt-4o", temperature=0.5)
```

### 3. Chain of Responsibility (Middleware)

Middleware handlers process requests in priority order:

```
Request -> [Limits] -> [PII] -> [HITL] -> [Retry] -> [Fallback] -> [Summarization] -> [Style] -> [Citations] -> Handler
```

### 4. State Graph (LangGraph)

Workflow defined as nodes and edges:

```python
graph.set_entry_point("researcher")
graph.add_edge("researcher", "writer")
graph.add_conditional_edges("editor", route_fn, {...})
graph.add_edge("diagrammer", END)
```

---

## Configuration Philosophy

### YAML for Data, Python for Logic

| Type | Location | Format |
|------|----------|--------|
| Agent definitions | `config/agents.yaml` | YAML |
| Middleware policies | `config/policy.yaml` | YAML |
| Style profiles | `config/style_profiles/*.json` | JSON |
| Application settings | `config/settings.py` | Python |
| Agent prompts | `prompts/*.yaml` | YAML |

### Policy Configuration Structure

```yaml
# config/policy.yaml
limits:
  max_model_calls_per_run: 30
  max_tool_calls_per_run: 50
  max_depth_per_run: 8

hitl:
  gate_web_fetch_unknown_domain: true
  allow_domains:
    - kafka.apache.org
    - confluent.io
  deny_domains:
    - malicious-site.com

tool_binding:
  researcher:
    allowed: [web.search, web.fetch]
    denied: []
  writer:
    allowed: [seo.readability]
    denied: [web.fetch, web.search]
```

---

## Middleware Pattern

### Handler Structure

Every middleware handler MUST implement these methods:

```python
class MyHandler(MiddlewareHandler):
    """
    Handler description.

    Priority: XXX (position in chain)
    Phase 2 Implementation.
    """

    def __init__(self, config: dict[str, Any], priority: int = XXX):
        super().__init__(name="MyHandler", priority=priority)
        # Load config values with defaults
        self.setting = config.get("setting", default_value)

    def before_call(self, ctx: ExecutionContext) -> ExecutionContext:
        """Called before target execution."""
        return ctx

    def after_call(self, ctx: ExecutionContext, result: Any) -> tuple[ExecutionContext, Any]:
        """Called after target execution."""
        return ctx, result

    def on_error(self, ctx: ExecutionContext, error: Exception) -> tuple[ExecutionContext, Optional[Exception]]:
        """Called on errors. Return None to handle, Exception to propagate."""
        return ctx, error

    def pre_process(self, state: dict[str, Any]) -> dict[str, Any]:
        """State pre-processing (simplified interface)."""
        return state

    def post_process(self, state: dict[str, Any]) -> dict[str, Any]:
        """State post-processing (simplified interface)."""
        return state
```

### Priority Levels

| Priority | Handler | Purpose |
|----------|---------|---------|
| 100 | LimitsHandler | Resource limits |
| 200 | PIIHandler | PII redaction |
| 300 | HITLHandler | Human approval |
| 400 | RetryHandler | Retry logic |
| 500 | FallbackHandler | Model fallback |
| 600 | SummarizationHandler | Context truncation |
| 700 | StyleInjectorHandler | Style profiles |
| 800 | CitationNormalizerHandler | Citation dedup |

---

## Agent Node Pattern

### Base Node Structure

All agent nodes MUST inherit from `BaseAgentNode`:

```python
class ResearcherNode(BaseAgentNode):
    """
    Researcher Agent Node - Gathers facts and citations.

    Context Slice: topic, requirements, existing facts
    Output: facts[], citations[], handoff to writer
    """

    def __init__(self, tool_binder: Optional[ToolBinder] = None):
        super().__init__(agent_name="researcher", tool_binder=tool_binder)

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """Execute research phase."""
        # 1. Get context slice
        context = self.get_context_slice(state)

        # 2. Execute tools
        results = self.call_tool("web.search", query=context["topic"])

        # 3. Update state
        state["facts"].extend(results)

        # 4. Handoff
        return self.handoff_to("writer", state, "Research complete")

    def get_context_slice(self, state: dict[str, Any]) -> dict[str, Any]:
        """Extract only what researcher needs."""
        return {
            "topic": state["tasks"][0]["topic"],
            "requirements": state["tasks"][0].get("requirements", []),
            "existing_facts": state.get("facts", []),
        }
```

### Node Function Pattern

For LangGraph compatibility, expose a module-level function:

```python
# At module level
_node_instance: Optional[ResearcherNode] = None

def researcher_node(state: dict[str, Any]) -> dict[str, Any]:
    """Researcher node function for LangGraph."""
    global _node_instance
    if _node_instance is None:
        _node_instance = ResearcherNode()
    return _node_instance.execute(state)
```

---

## State Management

### State Schema

The workflow state follows this structure:

```python
state = {
    # Task State
    "tasks": [{"task_id": str, "topic": str, "brief": str, "requirements": list}],
    "current_task_id": str,

    # Research State
    "facts": [{"claim_id": str, "text": str, "sources": list}],
    "citations": [{"source_id": str, "url": str, "title": str}],

    # Artifact State
    "artifacts": {"draft.md": {"content": str, "version": int}},
    "diagram_intents": [{"type": str, "description": str}],
    "diagrams": [{"drawio_xml": str, "title": str}],

    # Quality State
    "issues": [{"severity": str, "category": str, "description": str}],
    "editor_review": {"pass": bool, "critical_count": int},
    "iteration_count": int,

    # Workflow Metadata
    "run_id": str,
    "current_agent": str,
    "handoffs": [{"from": str, "to": str, "timestamp": str}],
    "workflow_status": "running" | "completed" | "failed",

    # Style & Config
    "style_profile": dict,
    "max_iterations": int,
}
```

### State Update Rules

1. **Never replace state** - Always return the full state with updates
2. **Append to lists** - Use `state["facts"].extend(new_facts)`, not assignment
3. **Track handoffs** - Always call `self.handoff_to()` when changing agents
4. **Increment counters** - Use `state["iteration_count"] = state.get("iteration_count", 0) + 1`

---

## Tool System

### Tool Binding Philosophy

**Principle**: Least privilege - agents only access what they need.

```python
# Tool access is POLICY-DRIVEN, not code-driven
# See config/policy.yaml for binding rules

# Good - Use tool binder
tools = tool_binder.get_tools_for_agent("researcher")
result = tool_binder.call_tool("researcher", "web.search", query=query)

# Avoid - Direct tool calls bypassing access control
result = search_web(query=query)  # No access control!
```

### Tool Adapter Pattern

Tools are adapted to a common interface:

```python
# tools/adapters.py
def search_web(query: str, max_results: int = 5) -> list[dict]:
    """
    Search the web using Tavily.

    Args:
        query: Search query
        max_results: Maximum results to return

    Returns:
        List of search results with url, title, snippet
    """
    # Implementation
    return results
```

---

## Error Handling

### Exception Hierarchy

```python
# Custom exceptions in relevant modules
class ToolAccessError(Exception):
    """Raised when agent accesses denied tool."""
    pass

class HITLDeniedError(Exception):
    """Raised when HITL approval is denied."""
    pass

class LimitExceededError(ValueError):
    """Raised when resource limits are exceeded."""
    pass
```

### Error Handling Pattern

```python
def execute(self, state: dict[str, Any]) -> dict[str, Any]:
    try:
        # Main logic
        result = self.call_tool("web.search", query=query)
    except ToolAccessError as e:
        logger.warning(f"Tool access denied: {e}")
        state["errors"].append({"type": "tool_access", "message": str(e)})
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        state["workflow_status"] = "failed"
        state["error_message"] = str(e)

    return state
```

---

## Logging Conventions

### Logger Setup

```python
import logging

logger = logging.getLogger(__name__)
```

### Log Levels

| Level | Use Case | Example |
|-------|----------|---------|
| `DEBUG` | Development details | `logger.debug(f"Loaded {len(items)} items")` |
| `INFO` | Normal operations | `logger.info(f"Processing topic: {topic}")` |
| `WARNING` | Recoverable issues | `logger.warning(f"Tool not found: {tool}")` |
| `ERROR` | Failures | `logger.error(f"API call failed: {e}")` |

### Logging Format

```python
# Include context in log messages
logger.info(f"[{agent_name}] Calling tool '{tool_name}'")
logger.warning(f"HITL denied for {ctx.tool_name}: {rationale}")
logger.error(f"Middleware {handler.name} before_call failed: {e}")
```

---

## Testing Guidelines

### Test Structure

```
tests/
├── unit/
│   ├── test_middleware.py      # Test handlers in isolation
│   ├── test_tool_binder.py     # Test access control
│   └── test_agent_nodes.py     # Test node logic
├── integration/
│   └── test_newsletter_workflow.py  # End-to-end tests
└── conftest.py                 # Shared fixtures
```

### Test Naming

```python
# test_<module>_<function>_<scenario>
def test_limits_handler_blocks_exceeded():
    ...

def test_hitl_simulator_policy_mode_denies_unknown_domain():
    ...
```

### Fixture Pattern

```python
@pytest.fixture
def sample_state():
    """Create sample workflow state for testing."""
    return create_initial_state(
        topic="Test Topic",
        brief="Test brief",
    )

@pytest.fixture
def mock_tool_binder():
    """Create tool binder with mock tools."""
    binder = ToolBinder()
    binder.register_tool("web.search", lambda **kw: [{"url": "test.com"}])
    return binder
```

---

## Documentation Standards

### Module Docstrings

```python
"""
Module Name - Short description.

Longer description of what this module does and its role
in the system.

Phase X Implementation.
"""
```

### Class Docstrings

```python
class MyClass:
    """
    Short description.

    Detailed explanation of the class purpose, when to use it,
    and any important notes.

    Attributes:
        attr1: Description
        attr2: Description
    """
```

### Function Docstrings (Google Style)

```python
def my_function(param1: str, param2: int = 10) -> dict[str, Any]:
    """
    Short description of function.

    Longer explanation if needed.

    Args:
        param1: Description of param1
        param2: Description of param2, defaults to 10

    Returns:
        Description of return value

    Raises:
        ValueError: When param1 is empty
    """
```

---

## File Naming Conventions

### Python Files

| Type | Convention | Example |
|------|------------|---------|
| Modules | `snake_case.py` | `tool_binder.py` |
| Test files | `test_<module>.py` | `test_tool_binder.py` |
| Private modules | `_private.py` | `_internal_utils.py` |

### Config Files

| Type | Convention | Example |
|------|------------|---------|
| YAML configs | `snake_case.yaml` | `agents.yaml`, `policy.yaml` |
| JSON profiles | `snake_case.json` | `neutral_concise.json` |

### Directories

| Type | Convention | Example |
|------|------------|---------|
| Package dirs | `snake_case/` | `middleware/`, `agents/` |
| Sub-packages | `snake_case/` | `handlers/`, `nodes/` |

---

## Import Organization

### Import Order

1. Standard library imports
2. Third-party imports
3. Local application imports

```python
# 1. Standard library
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Optional

# 2. Third-party
from langgraph.graph import StateGraph, END
import yaml

# 3. Local application
from agents.tool_binder import ToolBinder, get_tool_binder
from config import get_agent_config
from middleware.chain import MiddlewareChain
```

### Import Style

```python
# Good - Explicit imports
from typing import Any, Optional
from dataclasses import dataclass, field

# Good - Grouped from same package
from middleware.handlers import (
    LimitsHandler,
    PIIHandler,
    HITLHandler,
)

# Avoid - Star imports
from middleware.handlers import *

# Avoid - Unused imports
import os  # Not used anywhere
```

---

## Quick Reference

### Adding a New Agent

1. Add to `config/agents.yaml`
2. Create prompt in `prompts/<agent>.yaml`
3. Create node in `agents/nodes/<agent>_node.py`
4. Update `agents/nodes/__init__.py`
5. Add to workflow graph if needed

### Adding a New Middleware Handler

1. Create in `middleware/handlers/<handler>.py`
2. Follow the handler structure pattern
3. Add to `middleware/handlers/__init__.py`
4. Register in `middleware/chain.py` `_setup_chain()`
5. Add policy section to `config/policy.yaml`

### Adding a New Tool

1. Implement in `tools/adapters.py`
2. Register in `tool_binder.py` `create_tool_binder_with_adapters()`
3. Add binding rules to `config/policy.yaml` `tool_binding` section

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2024-11-24 | Initial conventions document |
