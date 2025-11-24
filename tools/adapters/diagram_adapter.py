"""
Diagram Adapter - Generates DrawIO diagrams and exports to PNG.

Not HITL gated.

Phase 2 Implementation.
"""

import logging
import uuid
from typing import Any

from tools.contracts import (
    DrawioGenerateInput,
    DrawioGenerateOutput,
    DrawioExportInput,
    DrawioExportOutput,
    DiagramNode,
    DiagramEdge,
)

logger = logging.getLogger(__name__)


# DrawIO style templates
STYLES = {
    "rectangle": "rounded=0;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;",
    "rounded": "rounded=1;whiteSpace=wrap;html=1;fillColor=#d5e8d4;strokeColor=#82b366;",
    "ellipse": "ellipse;whiteSpace=wrap;html=1;fillColor=#ffe6cc;strokeColor=#d79b00;",
    "diamond": "rhombus;whiteSpace=wrap;html=1;fillColor=#fff2cc;strokeColor=#d6b656;",
    "cylinder": "shape=cylinder3;whiteSpace=wrap;html=1;boundedLbl=1;size=15;fillColor=#f5f5f5;strokeColor=#666666;",
}

EDGE_STYLES = {
    "solid": "edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;endArrow=classic;",
    "dashed": "edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;dashed=1;endArrow=classic;",
    "dotted": "edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;dashed=1;dashPattern=1 2;endArrow=classic;",
}


class DiagramAdapter:
    """
    Adapter for diagram generation and export.

    Generates DrawIO XML from intent and exports to PNG.
    """

    def __init__(self, default_width: int = 650):
        self.default_width = default_width

    def generate(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Generate a DrawIO diagram from intent.

        Args:
            input_data: Dict matching DrawioGenerateInput schema

        Returns:
            Dict matching DrawioGenerateOutput schema
        """
        # Validate input
        try:
            validated_input = DrawioGenerateInput(**input_data)
        except Exception as e:
            logger.error(f"Invalid diagram input: {e}")
            raise ValueError(f"Invalid diagram input: {e}")

        logger.info(f"Generating {validated_input.diagram_type.value} diagram: {validated_input.title}")

        # Generate XML based on diagram type
        xml, node_count, edge_count = self._generate_xml(validated_input)

        # Generate filename
        filename = self._generate_filename(validated_input)

        # Create preview notes
        preview_notes = self._generate_preview(validated_input, node_count, edge_count)

        # Create output
        output = DrawioGenerateOutput(
            xml=xml,
            preview_notes=preview_notes,
            node_count=node_count,
            edge_count=edge_count,
            diagram_type=validated_input.diagram_type,
            filename_suggestion=filename,
        )

        return output.model_dump()

    def export(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Export DrawIO XML to PNG.

        Note: Actual PNG export requires drawio CLI or browser automation.
        This adapter provides the interface; real export is a Phase 3+ feature.

        Args:
            input_data: Dict matching DrawioExportInput schema

        Returns:
            Dict matching DrawioExportOutput schema
        """
        # Validate input
        try:
            validated_input = DrawioExportInput(**input_data)
        except Exception as e:
            logger.error(f"Invalid export input: {e}")
            raise ValueError(f"Invalid export input: {e}")

        logger.info(f"Exporting diagram to {validated_input.format.value}")

        # For Phase 2, we return a placeholder
        # Real export would use drawio CLI or browser automation
        output = DrawioExportOutput(
            png_path_or_b64="[PNG export requires drawio CLI - placeholder for Phase 2]",
            format=validated_input.format,
            width=650,
            height=400,
            file_size_bytes=0,
        )

        return output.model_dump()

    def _generate_xml(self, input_data: DrawioGenerateInput) -> tuple[str, int, int]:
        """Generate DrawIO XML from input."""
        diagram_id = str(uuid.uuid4())[:8]
        width = input_data.width or self.default_width

        # Start XML
        xml_parts = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<mxfile host="app.diagrams.net">',
            f'  <diagram name="{input_data.title}" id="{diagram_id}">',
            f'    <mxGraphModel dx="{width}" dy="400" grid="1" gridSize="10">',
            "      <root>",
            '        <mxCell id="0"/>',
            '        <mxCell id="1" parent="0"/>',
        ]

        # Add nodes
        node_count = 0
        for i, node in enumerate(input_data.nodes):
            node_xml = self._generate_node_xml(node, i)
            xml_parts.append(node_xml)
            node_count += 1

        # Add edges
        edge_count = 0
        for i, edge in enumerate(input_data.edges):
            edge_xml = self._generate_edge_xml(edge, i)
            xml_parts.append(edge_xml)
            edge_count += 1

        # Close XML
        xml_parts.extend(
            [
                "      </root>",
                "    </mxGraphModel>",
                "  </diagram>",
                "</mxfile>",
            ]
        )

        return "\n".join(xml_parts), node_count, edge_count

    def _generate_node_xml(self, node: DiagramNode, index: int) -> str:
        """Generate XML for a single node."""
        node_id = node.id or f"node_{index}"
        style = STYLES.get(node.type, STYLES["rectangle"])

        # Calculate position (simple grid layout)
        x = 50 + (index % 3) * 200
        y = 50 + (index // 3) * 100
        width = 120
        height = 60

        return f"""        <mxCell id="{node_id}" value="{node.label}" style="{style}" vertex="1" parent="1">
          <mxGeometry x="{x}" y="{y}" width="{width}" height="{height}" as="geometry"/>
        </mxCell>"""

    def _generate_edge_xml(self, edge: DiagramEdge, index: int) -> str:
        """Generate XML for a single edge."""
        edge_id = f"edge_{index}"
        style = EDGE_STYLES.get(edge.style, EDGE_STYLES["solid"])
        label = edge.label or ""

        return f"""        <mxCell id="{edge_id}" value="{label}" style="{style}" edge="1" parent="1" source="{edge.source}" target="{edge.target}">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>"""

    def _generate_filename(self, input_data: DrawioGenerateInput) -> str:
        """Generate a stable filename for the diagram."""
        # Sanitize title for filename
        title = input_data.title.lower()
        title = "".join(c if c.isalnum() or c in "- " else "" for c in title)
        title = title.replace(" ", "_")[:30]

        diagram_type = input_data.diagram_type.value

        return f"{title}_{diagram_type}.drawio"

    def _generate_preview(
        self,
        input_data: DrawioGenerateInput,
        node_count: int,
        edge_count: int,
    ) -> str:
        """Generate human-readable preview notes."""
        parts = [
            f"**{input_data.title}**",
            f"Type: {input_data.diagram_type.value}",
            f"Components: {node_count} nodes, {edge_count} connections",
            "",
            "**Intent:**",
            input_data.intent,
            "",
            "**Nodes:**",
        ]

        for node in input_data.nodes[:5]:
            parts.append(f"- {node.label}")

        if len(input_data.nodes) > 5:
            parts.append(f"- ... and {len(input_data.nodes) - 5} more")

        return "\n".join(parts)


# Singleton instance
_adapter = DiagramAdapter()


def generate_diagram(
    intent: str,
    diagram_type: str,
    title: str,
    nodes: list[dict[str, Any]] | None = None,
    edges: list[dict[str, Any]] | None = None,
    width: int = 650,
) -> dict[str, Any]:
    """
    Generate a DrawIO diagram.

    Args:
        intent: What the diagram should illustrate
        diagram_type: Type of diagram (architecture, data_flow, etc.)
        title: Diagram title
        nodes: List of node definitions
        edges: List of edge definitions
        width: Target width in pixels

    Returns:
        Dict with XML and metadata
    """
    input_data = {
        "intent": intent,
        "diagram_type": diagram_type,
        "title": title,
        "nodes": nodes or [],
        "edges": edges or [],
        "width": width,
    }
    return _adapter.generate(input_data)


def export_diagram(xml: str, format: str = "png", scale: float = 1.0) -> dict[str, Any]:
    """
    Export DrawIO XML to image format.

    Args:
        xml: DrawIO XML content
        format: Export format (png, svg)
        scale: Scale factor

    Returns:
        Dict with export result
    """
    input_data = {
        "xml": xml,
        "format": format,
        "scale": scale,
    }
    return _adapter.export(input_data)
