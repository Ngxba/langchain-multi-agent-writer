"""
Unit tests for tool binder.

Tests:
- Tool access control
- Tool registration
- Agent-tool binding

Phase 2 Implementation.
"""

import pytest

from agents.tool_binder import ToolBinder, ToolAccessError


# -----------------------------------------------------------------------------
# Test Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture
def tool_binder():
    """Create a tool binder with default policy."""
    return ToolBinder()


@pytest.fixture
def mock_tools():
    """Create mock tool functions."""

    def mock_search(query: str, k: int = 5):
        return {"results": [{"title": f"Result for {query}"}]}

    def mock_fetch(url: str):
        return {"content": f"Content from {url}"}

    def mock_readability(markdown: str):
        return {"fk_grade": 10.0, "word_count": len(markdown.split())}

    def mock_diagram(intent: str, diagram_type: str):
        return {"xml": "<diagram/>"}

    return {
        "web.search": mock_search,
        "web.fetch": mock_fetch,
        "seo.readability": mock_readability,
        "drawio.generate": mock_diagram,
    }


# -----------------------------------------------------------------------------
# Tool Registration Tests
# -----------------------------------------------------------------------------


class TestToolRegistration:
    """Tests for tool registration."""

    def test_register_single_tool(self, tool_binder, mock_tools):
        """Test registering a single tool."""
        tool_binder.register_tool("web.search", mock_tools["web.search"])

        assert "web.search" in tool_binder._tool_registry

    def test_register_multiple_tools(self, tool_binder, mock_tools):
        """Test registering multiple tools at once."""
        tool_binder.register_tools(mock_tools)

        assert "web.search" in tool_binder._tool_registry
        assert "web.fetch" in tool_binder._tool_registry
        assert "seo.readability" in tool_binder._tool_registry
        assert "drawio.generate" in tool_binder._tool_registry


# -----------------------------------------------------------------------------
# Tool Access Control Tests
# -----------------------------------------------------------------------------


class TestToolAccessControl:
    """Tests for tool access control."""

    def test_researcher_can_access_search(self, tool_binder):
        """Test that researcher can access web.search."""
        assert tool_binder.is_tool_allowed("researcher", "web.search") is True

    def test_researcher_can_access_fetch(self, tool_binder):
        """Test that researcher can access web.fetch."""
        assert tool_binder.is_tool_allowed("researcher", "web.fetch") is True

    def test_writer_cannot_access_fetch(self, tool_binder):
        """Test that writer cannot access web.fetch."""
        assert tool_binder.is_tool_allowed("writer", "web.fetch") is False

    def test_writer_cannot_access_search(self, tool_binder):
        """Test that writer cannot access web.search."""
        assert tool_binder.is_tool_allowed("writer", "web.search") is False

    def test_writer_can_access_readability(self, tool_binder):
        """Test that writer can access seo.readability."""
        assert tool_binder.is_tool_allowed("writer", "seo.readability") is True

    def test_editor_can_access_readability(self, tool_binder):
        """Test that editor can access seo.readability."""
        assert tool_binder.is_tool_allowed("editor", "seo.readability") is True

    def test_editor_cannot_access_fetch(self, tool_binder):
        """Test that editor cannot access web.fetch."""
        assert tool_binder.is_tool_allowed("editor", "web.fetch") is False

    def test_diagrammer_can_access_drawio(self, tool_binder):
        """Test that diagrammer can access drawio tools."""
        assert tool_binder.is_tool_allowed("diagrammer", "drawio.generate") is True
        assert tool_binder.is_tool_allowed("diagrammer", "drawio.export") is True

    def test_diagrammer_can_access_search(self, tool_binder):
        """Test that diagrammer can access web.search for research."""
        assert tool_binder.is_tool_allowed("diagrammer", "web.search") is True


# -----------------------------------------------------------------------------
# Tool Execution Tests
# -----------------------------------------------------------------------------


class TestToolExecution:
    """Tests for tool execution with access control."""

    def test_call_allowed_tool(self, tool_binder, mock_tools):
        """Test calling an allowed tool."""
        tool_binder.register_tools(mock_tools)

        result = tool_binder.call_tool("researcher", "web.search", query="kafka")

        assert "results" in result

    def test_call_denied_tool_raises_error(self, tool_binder, mock_tools):
        """Test that calling a denied tool raises ToolAccessError."""
        tool_binder.register_tools(mock_tools)

        with pytest.raises(ToolAccessError, match="not allowed"):
            tool_binder.call_tool("writer", "web.fetch", url="http://example.com")

    def test_call_unregistered_tool_raises_error(self, tool_binder):
        """Test that calling an unregistered tool raises ValueError."""
        with pytest.raises(ValueError, match="not registered"):
            tool_binder.call_tool("researcher", "nonexistent.tool")


# -----------------------------------------------------------------------------
# Get Tools for Agent Tests
# -----------------------------------------------------------------------------


class TestGetToolsForAgent:
    """Tests for getting tools for specific agents."""

    def test_get_tools_for_researcher(self, tool_binder, mock_tools):
        """Test getting tools for researcher."""
        tool_binder.register_tools(mock_tools)

        tools = tool_binder.get_tools_for_agent("researcher")

        assert "web.search" in tools
        assert "web.fetch" in tools

    def test_get_tools_for_writer(self, tool_binder, mock_tools):
        """Test getting tools for writer."""
        tool_binder.register_tools(mock_tools)

        tools = tool_binder.get_tools_for_agent("writer")

        assert "seo.readability" in tools
        assert "web.search" not in tools
        assert "web.fetch" not in tools

    def test_get_tools_for_diagrammer(self, tool_binder, mock_tools):
        """Test getting tools for diagrammer."""
        tool_binder.register_tools(mock_tools)

        tools = tool_binder.get_tools_for_agent("diagrammer")

        assert "drawio.generate" in tools
        assert "web.search" in tools

    def test_tools_are_callable(self, tool_binder, mock_tools):
        """Test that returned tools are callable."""
        tool_binder.register_tools(mock_tools)

        tools = tool_binder.get_tools_for_agent("researcher")

        for tool_name, tool_func in tools.items():
            assert callable(tool_func)


# -----------------------------------------------------------------------------
# Policy Loading Tests
# -----------------------------------------------------------------------------


class TestPolicyLoading:
    """Tests for policy loading."""

    def test_default_policy_loaded(self, tool_binder):
        """Test that default policy is loaded when no file provided."""
        assert len(tool_binder.tool_binding) > 0
        assert "researcher" in tool_binder.tool_binding
        assert "writer" in tool_binder.tool_binding
        assert "editor" in tool_binder.tool_binding
        assert "diagrammer" in tool_binder.tool_binding

    def test_get_allowed_tools_list(self, tool_binder):
        """Test getting allowed tools list."""
        allowed = tool_binder.get_allowed_tools("researcher")

        assert isinstance(allowed, list)
        assert "web.search" in allowed

    def test_get_denied_tools_list(self, tool_binder):
        """Test getting denied tools list."""
        denied = tool_binder.get_denied_tools("writer")

        assert isinstance(denied, list)
        assert "web.fetch" in denied
