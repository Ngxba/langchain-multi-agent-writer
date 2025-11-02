# BigData Newsletter Generator

A modular multi-agent AI system built with LangChain for creating detailed, engaging BigData newsletters through specialized agent collaboration.

## Overview

This system uses a **collaborative agent swarm** architecture where five specialized AI agents work together to research, plan, write, edit, and visualize BigData content.

### 🤖 Agents

| Agent | Role | Capabilities |
|-------|------|--------------|
| **Researcher** | Information Gathering | Web search, knowledge base queries, statistics collection |
| **Planner** | Content Structure | Newsletter planning, section organization, audience targeting |
| **Writer** | Content Creation | Technical writing, BigData expertise, engaging narratives |
| **Editor** | Quality Assurance | Review, refinement, fact-checking, style improvements |
| **Diagram Creator** | Visualization | DrawIO diagram generation for architectures and data flows |

### ✨ Key Features

- **Collaborative Swarm**: Agents dynamically transfer between each other based on task needs
- **Web Search**: Integration with Tavily for latest BigData news and trends
- **Knowledge Base**: Curated BigData domain knowledge (Kafka, Spark, Data Lakes, etc.)
- **Diagram Generation**: Automatic DrawIO XML generation for visualizations
- **Token Tracking**: Per-agent token usage and cost monitoring
- **Modular Architecture**: Highly organized codebase for easy extension

## 📁 Project Structure

```
langchain-multi-agent-writer/
├── agents/                      # Agent definitions
│   ├── researcher.py           # Research specialist
│   ├── planner.py             # Content planner
│   ├── writer.py              # BigData writer
│   ├── editor.py              # Quality reviewer
│   └── diagram_creator.py     # Diagram generator
├── tools/                      # Agent tools
│   ├── web_search.py          # Tavily web search
│   ├── knowledge_base.py      # Local knowledge retrieval
│   └── diagram_tools.py       # DrawIO XML generation
├── prompts/                    # Agent prompts
│   └── agent_prompts.py       # System prompts for all agents
├── workflows/                  # Orchestration
│   └── newsletter_swarm.py    # Main swarm workflow
├── config/                     # Configuration
│   └── settings.py            # Settings and constants
├── data/                       # Data files
│   └── bigdata_knowledge.json # BigData domain knowledge
├── outputs/                    # Generated content
│   └── diagrams/              # DrawIO diagrams
├── token_tracker.py           # Token tracking utility
├── newsletter_app.py          # Main application
└── main.py                    # Simple demo example
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- OpenAI API key
- (Optional) Tavily API key for web search

### Installation

1. **Clone the repository**

```bash
cd langchain-multi-agent-writer
```

2. **Set up environment**

Create a `.env` file:

```bash
OPENAI_API_KEY=your_openai_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here  # Optional
```

3. **Install dependencies**

Using uv (recommended):
```bash
uv sync
```

Or using pip:
```bash
pip install langchain langchain-openai langgraph langgraph-swarm python-dotenv
```

### Run the Newsletter Generator

```bash
python newsletter_app.py
```

This will generate a newsletter about "Apache Kafka in 2025" by default.

### Run Simple Demo

To see a basic agent swarm example:

```bash
python main.py
```

## 📖 Usage

### Basic Usage

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

### Customizing Topics

Edit `newsletter_app.py` to change the topic:

```python
topic = "Your BigData Topic Here"

result = swarm.generate_newsletter(
    topic=topic,
    additional_instructions="Any specific requirements..."
)
```

### Available BigData Topics

The knowledge base includes information about:
- **Stream Processing**: Apache Kafka, Flink, Spark Streaming
- **Batch Processing**: Apache Spark, Hadoop
- **Data Storage**: Data Lakes, Delta Lake, Apache Iceberg
- **Architectures**: Data Mesh, Lakehouse, Data Fabric
- **Analytics**: Real-time analytics, ETL/ELT pipelines

## 🔧 Configuration

### Agent Configuration

Edit `config/settings.py` to customize agent behavior:

```python
AGENT_CONFIG = {
    "researcher": {
        "model": "gpt-4o",
        "temperature": 0.7  # Adjust creativity
    },
    # ... other agents
}
```

### Newsletter Configuration

```python
NEWSLETTER_CONFIG = {
    "default_sections": [...],
    "target_word_count": 800,
    "tone": "professional yet engaging",
    "audience": "data engineers and architects"
}
```

## 📊 Token Tracking

The system automatically tracks:
- Per-agent token usage
- Cost calculation (based on GPT-4o pricing)
- Call counts and averages
- Session history

```python
# Get compact summary
print(swarm.get_compact_summary())
# Output: 💰 Tokens: 1,234 | Cost: $0.0567 | Calls: 12

# Get detailed report
print(swarm.get_token_report())
# Shows per-agent breakdown, costs, and call history
```

## 🎨 Diagram Generation

Agents can create DrawIO diagrams:

```python
# Data flow diagram
create_data_flow_diagram(
    title="Kafka Pipeline",
    components_str="Kafka:source,Spark:process,S3:storage",
    connections_str="Kafka->Spark:events;Spark->S3:data"
)

# Architecture diagram
create_architecture_diagram(
    title="Data Lakehouse",
    layers_str="Ingestion:Kafka;Processing:Spark;Storage:Delta Lake"
)
```

Diagrams are saved to `outputs/diagrams/` as `.drawio` files.

## 🌐 Web Search

The system uses Tavily for web search. If `TAVILY_API_KEY` is not set, it falls back to mock search results with realistic BigData content.

To use real web search:
1. Get API key from https://tavily.com
2. Add to `.env`: `TAVILY_API_KEY=your_key_here`

## 🧪 Extending the System

### Adding a New Agent

1. Create agent file in `agents/`:

```python
# agents/fact_checker.py
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

def create_fact_checker_agent():
    model = ChatOpenAI(model="gpt-4o", tags=["fact_checker"])
    tools = [...]  # Your tools
    return create_react_agent(model, tools, prompt="...", name="fact_checker")
```

2. Add to swarm in `workflows/newsletter_swarm.py`

3. Add handoff tools to connect with other agents

### Adding New Tools

1. Create tool function in `tools/`:

```python
# tools/my_tool.py
def my_tool(query: str) -> str:
    """Tool description for the agent."""
    # Implementation
    return result
```

2. Add to relevant agents in `agents/`

### Adding Domain Knowledge

Edit `data/bigdata_knowledge.json` to add new topics, trends, or statistics.

## 📝 Example Workflow

A typical newsletter generation follows this flow:

```
User Request
    ↓
Planner (structures the newsletter)
    ↓
Researcher (gathers information)
    ↓
Writer (drafts content)
    ↓
Diagram Creator (creates visualizations) [optional]
    ↓
Editor (reviews and refines)
    ↓
Final Newsletter
```

Agents can transfer between each other as needed. For example:
- Writer can request more research
- Editor can send back to Writer for revisions
- Any agent can request diagrams

## 💡 Tips

1. **Cost Management**: Monitor token usage with detailed reports
2. **Quality**: Let agents iterate - transfers improve quality
3. **Diagrams**: Request diagrams for complex architectures
4. **Web Search**: Use for latest news; knowledge base for fundamentals
5. **Customization**: Adjust temperature settings for creativity vs consistency

## 🐛 Troubleshooting

**Issue**: No web search results
- **Solution**: Check `TAVILY_API_KEY` in `.env` or use mock mode

**Issue**: Agents not transferring
- **Solution**: Check handoff tools are properly configured in each agent

**Issue**: High token usage
- **Solution**: Reduce temperature, simplify prompts, or limit iterations

## 📚 Learn More

- [LangChain Documentation](https://python.langchain.com/)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Multi-Agent Systems](https://python.langchain.com/docs/use_cases/agent_teams/)

## 🤝 Contributing

This is a modular system designed for easy extension. Feel free to:
- Add new agents
- Create custom tools
- Expand the knowledge base
- Improve prompts
- Add new workflows

## 📄 License

MIT License - feel free to use and modify for your needs.

---

**Built with LangChain, LangGraph, and OpenAI GPT-4o**
