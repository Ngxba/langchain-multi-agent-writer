"""
Diagrammer Node - Visual diagram generation.

Context: diagram_intents[], draft_sections
Produces: diagrams[], diagram_pngs[], placement_notes
Tools: drawio.generate, drawio.export, web.search

Phase 2 Implementation.
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Optional

from .base_node import BaseAgentNode

logger = logging.getLogger(__name__)


class DiagrammerNode(BaseAgentNode):
    """
    Diagrammer agent node.

    Transforms diagram intents into DrawIO diagrams and PNG exports.
    Ensures email-friendly sizing (650px max width).
    """

    # Size constraints
    MAX_WIDTH = 650
    DEFAULT_WIDTH = 600
    MAX_NODES = 15
    MAX_LABEL_LENGTH = 30

    # Color palette
    COLORS = {
        "primary": {"fill": "#dae8fc", "stroke": "#6c8ebf"},
        "secondary": {"fill": "#d5e8d4", "stroke": "#82b366"},
        "accent": {"fill": "#ffe6cc", "stroke": "#d79b00"},
        "warning": {"fill": "#fff2cc", "stroke": "#d6b656"},
        "neutral": {"fill": "#f5f5f5", "stroke": "#666666"},
    }

    def __init__(self, **kwargs):
        super().__init__(agent_name="diagrammer", **kwargs)

    def get_context_slice(self, state: dict[str, Any]) -> dict[str, Any]:
        """Extract diagrammer's context slice."""
        return {
            "diagram_intents": state.get("diagram_intents", []),
            "draft_sections": self._extract_sections(state.get("artifacts", {}).get("draft.md", {}).get("content", "")),
            "existing_diagrams": state.get("diagrams", []),
            "topic": self._get_topic(state),
        }

    def _get_topic(self, state: dict[str, Any]) -> str:
        """Extract topic from state."""
        if "tasks" in state and state["tasks"]:
            task = state["tasks"][0] if isinstance(state["tasks"], list) else state["tasks"]
            if isinstance(task, dict):
                return task.get("topic", "Unknown Topic")
        return "Unknown Topic"

    def _extract_sections(self, draft: str) -> list[dict]:
        """Extract sections from draft for diagram placement."""
        sections: list[dict] = []
        if not draft:
            return sections

        import re

        # Match ## headings
        pattern = r"^##\s+(.+)$"
        for i, match in enumerate(re.finditer(pattern, draft, re.MULTILINE)):
            sections.append(
                {
                    "index": i,
                    "title": match.group(1).strip(),
                    "position": match.start(),
                }
            )

        return sections

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """
        Execute diagram generation.

        1. Get context slice
        2. Process each diagram intent
        3. Generate DrawIO XML
        4. Export to PNG
        5. Document placement
        6. Update state
        """
        logger.info("Diagrammer node executing")

        # Get context
        context = self.get_context_slice(state)
        intents = context.get("diagram_intents", [])
        topic = context.get("topic", "Unknown")

        if not intents:
            logger.info("No diagram intents to process")
            state["diagrams_completed"] = True
            state["workflow_complete"] = True
            return state

        # Process each intent
        diagrams = []
        diagram_pngs = []
        placement_notes = []

        for intent in intents[:5]:  # Limit to 5 diagrams
            try:
                result = self._process_intent(intent, topic)
                if result:
                    diagrams.append(result["diagram"])
                    if result.get("png"):
                        diagram_pngs.append(result["png"])
                    placement_notes.append(result["placement"])
            except Exception as e:
                logger.error(f"Failed to process diagram intent: {e}")

        # Update state
        state["diagrams"] = diagrams
        state["diagram_pngs"] = diagram_pngs
        state["placement_notes"] = placement_notes

        # Store artifacts
        if "artifacts" not in state:
            state["artifacts"] = {}

        for i, diagram in enumerate(diagrams):
            artifact_name = f"diagram_{i + 1}.drawio"
            state["artifacts"][artifact_name] = {
                "name": artifact_name,
                "content": diagram.get("xml", ""),
                "content_type": "application/xml",
                "created_at": datetime.now().isoformat(),
                "created_by": "diagrammer",
                "metadata": {
                    "intent_id": diagram.get("intent_id"),
                    "diagram_type": diagram.get("type"),
                },
            }

        # Mark workflow complete
        state["diagrams_completed"] = True
        state["workflow_complete"] = True
        state["completion_timestamp"] = datetime.now().isoformat()

        logger.info(f"Generated {len(diagrams)} diagrams")
        return state

    def _process_intent(self, intent: dict, topic: str) -> Optional[dict]:
        """Process a single diagram intent."""
        intent_id = intent.get("intent_id", f"DIAG_{uuid.uuid4().hex[:6].upper()}")
        diagram_type = intent.get("diagram_type", "architecture")
        title = intent.get("title", f"{topic} Diagram")
        description = intent.get("description", "")
        placement_hint = intent.get("placement_hint", "After introduction")

        # Get nodes and edges from intent or generate defaults
        nodes = intent.get("nodes", [])
        edges = intent.get("edges", [])

        if not nodes:
            # Generate default nodes based on diagram type and topic
            nodes, edges = self._generate_default_content(diagram_type, topic)

        # Validate constraints
        nodes = nodes[: self.MAX_NODES]  # Enforce node limit
        for node in nodes:
            if len(node.get("label", "")) > self.MAX_LABEL_LENGTH:
                node["label"] = node["label"][: self.MAX_LABEL_LENGTH - 3] + "..."

        # Generate DrawIO XML
        xml = self._generate_drawio_xml(intent_id, title, diagram_type, nodes, edges)

        # Try to export PNG if tool available
        png_data = None
        if "drawio.export" in self.tools:
            try:
                png_result = self.call_tool("drawio.export", xml=xml, format="png")
                png_data = png_result.get("data")
            except Exception as e:
                logger.warning(f"PNG export failed: {e}")

        # Create placement note
        placement = {
            "diagram_id": intent_id,
            "filename": f"{intent_id.lower()}.png",
            "placement": placement_hint,
            "alt_text": f"{title} - {description}",
            "caption": f"Figure: {title}",
        }

        return {
            "diagram": {
                "intent_id": intent_id,
                "type": diagram_type,
                "title": title,
                "xml": xml,
                "node_count": len(nodes),
                "edge_count": len(edges),
            },
            "png": png_data,
            "placement": placement,
        }

    def _generate_default_content(
        self,
        diagram_type: str,
        topic: str,
    ) -> tuple[list[dict], list[dict]]:
        """Generate default nodes and edges for a diagram type."""
        nodes = []
        edges = []

        if diagram_type == "architecture":
            # Default architecture diagram
            nodes = [
                {"id": "n1", "label": "Client", "type": "rectangle", "x": 250, "y": 50},
                {"id": "n2", "label": "API Gateway", "type": "rounded", "x": 250, "y": 150},
                {"id": "n3", "label": "Service Layer", "type": "rounded", "x": 250, "y": 250},
                {"id": "n4", "label": "Database", "type": "cylinder", "x": 250, "y": 350},
            ]
            edges = [
                {"source": "n1", "target": "n2", "label": "HTTP"},
                {"source": "n2", "target": "n3", "label": ""},
                {"source": "n3", "target": "n4", "label": "Query"},
            ]

        elif diagram_type == "data_flow":
            # Default data flow diagram
            nodes = [
                {"id": "n1", "label": "Source", "type": "rectangle", "x": 50, "y": 150},
                {"id": "n2", "label": "Process", "type": "rounded", "x": 200, "y": 150},
                {"id": "n3", "label": "Transform", "type": "rounded", "x": 350, "y": 150},
                {"id": "n4", "label": "Sink", "type": "rectangle", "x": 500, "y": 150},
            ]
            edges = [
                {"source": "n1", "target": "n2", "label": "Input"},
                {"source": "n2", "target": "n3", "label": ""},
                {"source": "n3", "target": "n4", "label": "Output"},
            ]

        elif diagram_type == "sequence":
            # Default sequence diagram
            nodes = [
                {"id": "n1", "label": "Client", "type": "rectangle", "x": 100, "y": 50},
                {"id": "n2", "label": "Server", "type": "rectangle", "x": 300, "y": 50},
                {"id": "n3", "label": "Database", "type": "cylinder", "x": 500, "y": 50},
            ]
            edges = [
                {"source": "n1", "target": "n2", "label": "Request"},
                {"source": "n2", "target": "n3", "label": "Query"},
                {"source": "n3", "target": "n2", "label": "Result", "style": "dashed"},
                {"source": "n2", "target": "n1", "label": "Response", "style": "dashed"},
            ]

        else:
            # Generic block diagram
            nodes = [
                {"id": "n1", "label": f"{topic} Component 1", "type": "rectangle", "x": 100, "y": 100},
                {"id": "n2", "label": f"{topic} Component 2", "type": "rectangle", "x": 300, "y": 100},
                {"id": "n3", "label": f"{topic} Component 3", "type": "rectangle", "x": 200, "y": 250},
            ]
            edges = [
                {"source": "n1", "target": "n3", "label": ""},
                {"source": "n2", "target": "n3", "label": ""},
            ]

        return nodes, edges

    def _generate_drawio_xml(
        self,
        diagram_id: str,
        title: str,
        diagram_type: str,
        nodes: list[dict],
        edges: list[dict],
    ) -> str:
        """Generate DrawIO XML from nodes and edges."""
        # Node style templates
        primary = self.COLORS["primary"]
        secondary = self.COLORS["secondary"]
        accent = self.COLORS["accent"]
        warning = self.COLORS["warning"]
        neutral = self.COLORS["neutral"]
        node_styles = {
            "rectangle": f"rounded=0;whiteSpace=wrap;html=1;fillColor={primary['fill']};strokeColor={primary['stroke']};",
            "rounded": f"rounded=1;whiteSpace=wrap;html=1;fillColor={secondary['fill']};strokeColor={secondary['stroke']};",
            "ellipse": f"ellipse;whiteSpace=wrap;html=1;fillColor={accent['fill']};strokeColor={accent['stroke']};",
            "diamond": f"rhombus;whiteSpace=wrap;html=1;fillColor={warning['fill']};strokeColor={warning['stroke']};",
            "cylinder": (
                f"shape=cylinder3;whiteSpace=wrap;html=1;boundedLbl=1;backgroundOutline=1;size=15;"
                f"fillColor={neutral['fill']};strokeColor={neutral['stroke']};"
            ),
        }

        # Edge style templates
        edge_styles = {
            "solid": "edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;endArrow=classic;",
            "dashed": "edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;dashed=1;endArrow=classic;",
        }

        # Build XML
        graph_attrs = (
            f'dx="{self.DEFAULT_WIDTH}" dy="400" grid="1" gridSize="10" guides="1" tooltips="1" '
            f'connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="850" pageHeight="1100"'
        )
        xml_parts = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<mxfile host="app.diagrams.net" modified="' + datetime.now().isoformat() + '">',
            f'  <diagram name="{title}" id="{diagram_id}">',
            f"    <mxGraphModel {graph_attrs}>",
            "      <root>",
            '        <mxCell id="0"/>',
            '        <mxCell id="1" parent="0"/>',
        ]

        # Add nodes
        for node in nodes:
            node_id = node.get("id", f"node_{uuid.uuid4().hex[:6]}")
            label = node.get("label", "")
            node_type = node.get("type", "rectangle")
            x = node.get("x", 100)
            y = node.get("y", 100)
            width = node.get("width", 120)
            height = node.get("height", 60)

            style = node_styles.get(node_type, node_styles["rectangle"])

            xml_parts.append(f'        <mxCell id="{node_id}" value="{label}" style="{style}" vertex="1" parent="1">')
            xml_parts.append(f'          <mxGeometry x="{x}" y="{y}" width="{width}" height="{height}" as="geometry"/>')
            xml_parts.append("        </mxCell>")

        # Add edges
        for i, edge in enumerate(edges):
            edge_id = f"edge_{i + 1}"
            source = edge.get("source", "")
            target = edge.get("target", "")
            label = edge.get("label", "")
            edge_type = edge.get("style", "solid")

            style = edge_styles.get(edge_type, edge_styles["solid"])

            xml_parts.append(
                f'        <mxCell id="{edge_id}" value="{label}" style="{style}" edge="1" parent="1" source="{source}" target="{target}">'
            )
            xml_parts.append('          <mxGeometry relative="1" as="geometry"/>')
            xml_parts.append("        </mxCell>")

        # Close XML
        xml_parts.extend(
            [
                "      </root>",
                "    </mxGraphModel>",
                "  </diagram>",
                "</mxfile>",
            ]
        )

        return "\n".join(xml_parts)


# Singleton instance
_node: Optional[DiagrammerNode] = None


def get_diagrammer_node() -> DiagrammerNode:
    """Get the diagrammer node instance."""
    global _node
    if _node is None:
        _node = DiagrammerNode()
    return _node


def diagrammer_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    LangGraph node function for diagrammer.

    Args:
        state: Current workflow state

    Returns:
        Updated state
    """
    return get_diagrammer_node().execute(state)
