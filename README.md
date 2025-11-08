# Vietnamese Technical Newsletter - Multi-Agent System

> Streamlit application for multi-agent support in technical document writing

A modular multi-agent AI system built with LangChain, LangGraph, and Streamlit for creating detailed, engaging Vietnamese technical newsletters through specialized agent collaboration.

---

## 🚀 Quick Start (3 Steps)

### Step 1: Set Up Environment

```bash
# Copy the example .env file
cp .env.sample .env

# Edit .env and add your API keys
# Required:
# - OPENAI_API_KEY
# - TAVILY_API_KEY
# - ANTHROPIC_API_KEY
```

### Step 2: Install Dependencies

```bash
# Using uv (recommended)
uv sync

# Set up pre-commit hooks (optional)
uv run pre-commit install
uv run pre-commit run --all-files  # Run all checks
```

### Step 3: Launch the Research Swarm App

```bash
# Option 1: Use launcher script
./run_app.sh

# Option 2: Manual with uv
uv run streamlit run research_swarm_app.py
```

The app will open at `http://localhost:8501`

---

## 📋 Table of Contents

- [Overview](#overview)
- [Research Swarm App](#-research-swarm-streamlit-app)
- [Newsletter Generator](#-newsletter-generator-legacy)
- [Architecture](#-architecture)
- [Configuration](#-configuration)
- [Token Tracking](#-token-tracking)
- [Extending the System](#-extending-the-system)
- [Troubleshooting](#-troubleshooting)

---

## Overview

This system provides two main applications:

### 1. **Research Swarm** (New - Streamlit App)
Interactive chat interface for Vietnamese technical newsletter research with:
- **🎯 Research Strategist**: Creates comprehensive content briefs
- **🔬 Technical Researcher**: Gathers detailed technical information

### 2. **Newsletter Generator** (Original - CLI)
Full pipeline with five specialized agents:
- **Researcher**, **Planner**, **Writer**, **Editor**, **Diagram Creator**

---

## 🔬 Research Swarm (Streamlit App)

### Features

- **Interactive Chat Interface**: Step-by-step agent interaction
- **Real-time Agent Visualization**: See which agent is active
- **Transfer Indicators**: Watch agents hand off to each other
- **Tool Call Tracking**: Monitor web searches and actions
- **Export Conversations**: Download chat history as JSON
- **Vietnamese Style Guide**: Built-in style reference

### Visual Indicators

| Indicator | Meaning |
|-----------|---------|
| 🎯 Green Badge | Research Strategist active |
| 🔬 Blue Badge | Technical Researcher active |
| 🔄 Green Box | Agent transfer happening |
| 🔧 Yellow Box | Tool being used (e.g., web search) |
| ⚙️ Tool Result | Output from a tool |

### Usage Examples

#### Simple Topic Request
```
Create a content brief for Apache Kafka
```

#### Detailed Request
```
Create a comprehensive content brief for a Vietnamese technical newsletter on: Redis

Context:
- Audience: Vietnamese backend developers (intermediate level)
- Focus on caching and real-time applications
- Include Vietnamese or Southeast Asian examples

Please create the brief and transfer to Technical Researcher.
```

#### Follow-up Research
```
Can you search for specific performance benchmarks comparing Redis vs Memcached?
```

### Workflow

```
User Message
    ↓
🎯 Research Strategist
    ├─ Analyzes topic
    ├─ Creates content brief
    └─ 🔄 Transfers to...
        ↓
🔬 Technical Researcher
    ├─ 🔍 Searches web
    ├─ Gathers information
    └─ Returns research
        ↓
Results Displayed
```

### Example Topics

Click pre-built buttons in the app:
- Apache Flink - Stream Processing
- Redis - In-Memory Database
- Kubernetes - Container Orchestration
- Apache Kafka - Message Broker

### Sidebar Features

- **About**: Information about the Research Swarm
- **Agents**: View capabilities of each agent
- **Status**: Current active agent and message count
- **Actions**:
  - 🔄 New Conversation - Start fresh
  - 💾 Export Chat - Download as JSON
- **📋 Style Reference**: Vietnamese newsletter guidelines

---

## 📰 Newsletter Generator (Legacy)

The original full-pipeline newsletter generator with five specialized agents.

### Agents

| Agent | Role | Model | Temperature |
|-------|------|-------|-------------|
| **Researcher** | Information Gathering | GPT-4o | 0.7 |
| **Planner** | Content Structure | GPT-4o | 0.5 |
| **Writer** | Content Creation | GPT-4o | 0.8 |
| **Editor** | Quality Assurance | GPT-4o | 0.3 |
| **Diagram Creator** | Visualization | Claude Sonnet 4.5 | 0.2 |

### Running the Newsletter Generator

```bash
# Generate newsletter (default topic: Apache Kafka)
python newsletter_app.py

# Simple demo
python main.py
```

### Programmatic Usage

```python
from workflows.newsletter_swarm import create_newsletter_swarm

# Create the swarm
swarm = create_newsletter_swarm(enable_token_tracking=True)

# Generate a newsletter
result = swarm.generate_newsletter(
    topic="Apache Spark Performance Optimization",
    additional_instructions="Focus on practical tips and recent updates"
)

# Get token usage
print(swarm.get_token_report())
```

### Workflow

```
User Request
    ↓
Planner (structures newsletter)
    ↓
Researcher (gathers information)
    ↓
Writer (drafts content)
    ↓
Diagram Creator (visualizations - optional)
    ↓
Editor (reviews and refines)
    ↓
Final Newsletter
```

---

## 🏗️ Architecture

### Project Structure

```
langchain-multi-agent-writer/
├── agents/                      # Agent definitions
│   ├── research_strategist.py  # Content brief creator
│   ├── research_technical.py   # Technical researcher
│   ├── researcher.py           # Original researcher
│   ├── planner.py              # Content planner
│   ├── writer.py               # Technical writer
│   ├── editor.py               # Quality reviewer
│   └── diagram_creator.py      # Diagram generator
│
├── workflows/                   # Orchestration
│   ├── research_swarm.py       # Research Swarm workflow
│   └── newsletter_swarm.py     # Newsletter workflow
│
├── tools/                       # Agent tools
│   ├── web_search.py           # Tavily integration
│   └── diagram_tools.py        # DrawIO generation
│
├── prompts/                     # Agent prompts
│   ├── research_strategist.yaml
│   ├── research_technical.yaml
│   ├── style_reference.json    # Vietnamese style guide
│   └── agent_prompts.py        # Other prompts
│
├── config/                      # Configuration
│   ├── settings.py             # Agent configs
│   ├── agent_names.py          # Name constants
│   └── agent_handoffs.py       # Handoff configuration
│
├── utils/                       # Utilities
│   ├── agent_utils.py          # Helper functions
│   ├── output_writer.py        # File output
│   └── streamlit_helpers.py    # Streamlit utilities
│
├── experimentals/               # Notebooks
│   └── research_swarm_interactive.ipynb
│
├── outputs/                     # Generated content
│   └── diagrams/               # DrawIO files
│
├── research_swarm_app.py       # Streamlit application
├── newsletter_app.py           # CLI newsletter app
├── verify_setup.py             # Setup verification
└── token_tracker.py            # Token tracking
```

### Technology Stack

- **LangChain**: Agent framework
- **LangGraph**: Agent orchestration
- **LangGraph Swarm**: Multi-agent coordination
- **Streamlit**: Web interface
- **OpenAI GPT-4o**: Main agents
- **Claude Sonnet 4.5**: Diagram creator
- **Tavily**: Web search

---

## ⚙️ Configuration

### Environment Variables

Required in `.env`:

```bash
OPENAI_API_KEY=your_openai_key      # GPT-4o agents
TAVILY_API_KEY=your_tavily_key      # Web search
ANTHROPIC_API_KEY=your_claude_key   # Diagram creator
```

### Agent Configuration

Edit `config/settings.py`:

```python
AGENT_CONFIG = {
    "research_strategist": {
        "model": "gpt-4o",
        "temperature": 0.5,
        "description": "..."
    },
    "research_technical": {
        "model": "gpt-4o",
        "temperature": 0.5,
        "description": "..."
    },
    # ... other agents
}
```

### Agent Handoffs

Configure in `config/agent_handoffs.py`:

```python
AGENT_HANDOFFS = {
    RESEARCH_STRATEGIST: [
        (RESEARCH_TECHNICAL, "Transfer to Technical Researcher..."),
    ],
    RESEARCH_TECHNICAL: [
        (RESEARCH_STRATEGIST, "Transfer back to Strategist..."),
    ],
}
```

### Vietnamese Style Reference

Located at `prompts/style_reference.json`:
- Language rules (Vietnamese + English technical terms)
- Voice and tone guidelines
- Audience profiling
- Signature writing moves
- Formatting standards

---

## 📊 Token Tracking

```python
# Get compact summary
print(swarm.get_compact_summary())
# Output: 💰 Tokens: 1,234 | Cost: $0.0567 | Calls: 12

# Get detailed report
print(swarm.get_token_report())
```

---

## 🔧 Extending the System

### Adding a New Agent

```python
# agents/my_agent.py
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

def create_my_agent():
    model = ChatOpenAI(model="gpt-4o", temperature=0.5, tags=["my_agent"])
    return create_react_agent(model, tools=[...], prompt="...", name="my_agent")
```

Then add to `workflows/`, configure handoffs in `config/agent_handoffs.py`, and create prompt in `prompts/`

### Adding New Tools

```python
# tools/my_tool.py
def my_tool(query: str) -> str:
    """Tool description for the agent."""
    return result
```

---

## 🐛 Troubleshooting

**App won't start**
```bash
uv run python verify_setup.py
uv sync
```

**Agent transfers not working**
- Check sidebar for active agent and 🔄 transfer indicator
- Verify handoffs in `config/agent_handoffs.py`
- Check tool name matches in prompt (e.g., `transfer_to_research_technical` not `transfer_to_researcher_technical`)

**"No module named..."**
```bash
uv run streamlit run research_swarm_app.py  # Use uv run prefix
```

**Long wait times**
- Web searches take 10-30 seconds - watch for 🔧 tool indicators

**No web search results**
- Check `TAVILY_API_KEY` in `.env`

---

## 📚 Resources

- **CLAUDE.md** - Detailed architecture
- **verify_setup.py** - Setup verification
- **experimentals/** - Interactive notebooks
- [LangChain](https://python.langchain.com/) | [LangGraph](https://langchain-ai.github.io/langgraph/) | [LangGraph Swarm](https://github.com/langchain-ai/langgraph-swarm)

---

## 📄 License

MIT License

---

**Built with LangChain, LangGraph, Streamlit, GPT-4o, and Claude Sonnet 4.5**
