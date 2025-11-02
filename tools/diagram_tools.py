"""
Diagram generation tools for creating DrawIO visualizations.
"""

import os
import uuid
from typing import List, Dict, Optional
from datetime import datetime
from config.settings import DIAGRAMS_DIR, ensure_output_dirs


class DrawIODiagramGenerator:
    """Generator for DrawIO-compatible XML diagrams."""

    def __init__(self):
        """Initialize diagram generator."""
        ensure_output_dirs()

    def create_flow_diagram(
        self,
        title: str,
        components: List[Dict[str, str]],
        connections: List[Dict[str, str]]
    ) -> str:
        """
        Create a data flow diagram.

        Args:
            title: Diagram title
            components: List of components with 'name' and 'type' keys
            connections: List of connections with 'from', 'to', and 'label' keys

        Returns:
            Path to generated DrawIO file
        """
        diagram_xml = self._generate_flow_diagram_xml(title, components, connections)
        return self._save_diagram(diagram_xml, title)

    def create_architecture_diagram(
        self,
        title: str,
        layers: List[Dict[str, List[str]]]
    ) -> str:
        """
        Create a layered architecture diagram.

        Args:
            title: Diagram title
            layers: List of layers, each with 'name' and 'components' keys

        Returns:
            Path to generated DrawIO file
        """
        diagram_xml = self._generate_architecture_diagram_xml(title, layers)
        return self._save_diagram(diagram_xml, title)

    def _generate_flow_diagram_xml(
        self,
        title: str,
        components: List[Dict[str, str]],
        connections: List[Dict[str, str]]
    ) -> str:
        """Generate DrawIO XML for flow diagram."""
        # Simple XML structure for DrawIO
        xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
        xml += '<mxfile host="app.diagrams.net" modified="{}Z" version="21.0.0">\n'.format(
            datetime.utcnow().isoformat()
        )
        xml += '  <diagram name="{}" id="{}">\n'.format(title, str(uuid.uuid4()))
        xml += '    <mxGraphModel dx="1422" dy="794" grid="1" gridSize="10" guides="1">\n'
        xml += '      <root>\n'
        xml += '        <mxCell id="0" />\n'
        xml += '        <mxCell id="1" parent="0" />\n'

        # Add components
        cell_ids = {}
        x_pos = 100
        y_pos = 100

        for i, component in enumerate(components):
            cell_id = f"component_{i}"
            cell_ids[component['name']] = cell_id
            name = component.get('name', f'Component {i}')
            comp_type = component.get('type', 'process')

            # Different styles for different component types
            style = self._get_component_style(comp_type)

            xml += '        <mxCell id="{}" value="{}" style="{}" vertex="1" parent="1">\n'.format(
                cell_id, name, style
            )
            xml += '          <mxGeometry x="{}" y="{}" width="120" height="60" as="geometry" />\n'.format(
                x_pos, y_pos
            )
            xml += '        </mxCell>\n'

            x_pos += 180
            if (i + 1) % 3 == 0:
                x_pos = 100
                y_pos += 120

        # Add connections
        for i, conn in enumerate(connections):
            from_id = cell_ids.get(conn.get('from', ''))
            to_id = cell_ids.get(conn.get('to', ''))
            label = conn.get('label', '')

            if from_id and to_id:
                edge_id = f"edge_{i}"
                xml += '        <mxCell id="{}" value="{}" style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;strokeWidth=2;endArrow=classic;" edge="1" parent="1" source="{}" target="{}">\n'.format(
                    edge_id, label, from_id, to_id
                )
                xml += '          <mxGeometry relative="1" as="geometry" />\n'
                xml += '        </mxCell>\n'

        xml += '      </root>\n'
        xml += '    </mxGraphModel>\n'
        xml += '  </diagram>\n'
        xml += '</mxfile>\n'

        return xml

    def _generate_architecture_diagram_xml(
        self,
        title: str,
        layers: List[Dict[str, List[str]]]
    ) -> str:
        """Generate DrawIO XML for architecture diagram."""
        xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
        xml += '<mxfile host="app.diagrams.net" modified="{}Z" version="21.0.0">\n'.format(
            datetime.utcnow().isoformat()
        )
        xml += '  <diagram name="{}" id="{}">\n'.format(title, str(uuid.uuid4()))
        xml += '    <mxGraphModel dx="1422" dy="794" grid="1" gridSize="10" guides="1">\n'
        xml += '      <root>\n'
        xml += '        <mxCell id="0" />\n'
        xml += '        <mxCell id="1" parent="0" />\n'

        y_pos = 50

        for layer_idx, layer in enumerate(layers):
            layer_name = layer.get('name', f'Layer {layer_idx}')
            components = layer.get('components', [])

            # Add layer container
            layer_id = f"layer_{layer_idx}"
            xml += '        <mxCell id="{}" value="{}" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#e1d5e7;strokeColor=#9673a6;" vertex="1" parent="1">\n'.format(
                layer_id, layer_name
            )
            xml += '          <mxGeometry x="50" y="{}" width="700" height="150" as="geometry" />\n'.format(y_pos)
            xml += '        </mxCell>\n'

            # Add components within layer
            x_offset = 80
            for comp_idx, component in enumerate(components):
                comp_id = f"layer_{layer_idx}_comp_{comp_idx}"
                xml += '        <mxCell id="{}" value="{}" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;" vertex="1" parent="1">\n'.format(
                    comp_id, component
                )
                xml += '          <mxGeometry x="{}" y="{}" width="100" height="50" as="geometry" />\n'.format(
                    x_offset, y_pos + 70
                )
                xml += '        </mxCell>\n'
                x_offset += 120

            y_pos += 180

        xml += '      </root>\n'
        xml += '    </mxGraphModel>\n'
        xml += '  </diagram>\n'
        xml += '</mxfile>\n'

        return xml

    def _get_component_style(self, comp_type: str) -> str:
        """Get DrawIO style for component type."""
        styles = {
            "source": "rounded=0;whiteSpace=wrap;html=1;fillColor=#d5e8d4;strokeColor=#82b366;",
            "process": "rounded=1;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;",
            "storage": "shape=cylinder3;whiteSpace=wrap;html=1;fillColor=#ffe6cc;strokeColor=#d79b00;",
            "output": "rounded=0;whiteSpace=wrap;html=1;fillColor=#f8cecc;strokeColor=#b85450;",
            "decision": "rhombus;whiteSpace=wrap;html=1;fillColor=#fff2cc;strokeColor=#d6b656;"
        }
        return styles.get(comp_type, styles["process"])

    def _save_diagram(self, xml_content: str, title: str) -> str:
        """Save diagram XML to file."""
        filename = f"{title.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.drawio"
        filepath = os.path.join(DIAGRAMS_DIR, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(xml_content)

        return filepath


# Tool functions for LangChain agents
def create_data_flow_diagram(
    title: str,
    components_str: str,
    connections_str: str
) -> str:
    """
    Create a data flow diagram in DrawIO format.

    Use this to visualize how data flows through a system or pipeline.

    Args:
        title: Diagram title (e.g., "Kafka Streaming Pipeline")
        components_str: Comma-separated components in format "name:type" (e.g., "Kafka:source,Spark:process,S3:storage")
                       Types can be: source, process, storage, output, decision
        connections_str: Semicolon-separated connections in format "from->to:label" (e.g., "Kafka->Spark:events;Spark->S3:processed data")

    Returns:
        Path to generated diagram file and confirmation message

    Example:
        create_data_flow_diagram(
            "Kafka Pipeline",
            "Kafka:source,Spark Streaming:process,Data Lake:storage",
            "Kafka->Spark Streaming:events;Spark Streaming->Data Lake:processed data"
        )
    """
    # Parse components
    components = []
    for comp_str in components_str.split(','):
        parts = comp_str.strip().split(':')
        components.append({
            'name': parts[0].strip(),
            'type': parts[1].strip() if len(parts) > 1 else 'process'
        })

    # Parse connections
    connections = []
    for conn_str in connections_str.split(';'):
        if '->' in conn_str:
            parts = conn_str.split('->')
            from_comp = parts[0].strip()
            to_and_label = parts[1].split(':')
            to_comp = to_and_label[0].strip()
            label = to_and_label[1].strip() if len(to_and_label) > 1 else ''

            connections.append({
                'from': from_comp,
                'to': to_comp,
                'label': label
            })

    # Generate diagram
    generator = DrawIODiagramGenerator()
    filepath = generator.create_flow_diagram(title, components, connections)

    return f"✅ Diagram created successfully!\n\nFile: {filepath}\n\nThe diagram illustrates {title} and can be opened in DrawIO (diagrams.net) for viewing and editing."


def create_architecture_diagram(title: str, layers_str: str) -> str:
    """
    Create a layered architecture diagram in DrawIO format.

    Use this to visualize system architecture with multiple layers.

    Args:
        title: Diagram title (e.g., "Modern Data Architecture")
        layers_str: Semicolon-separated layers in format "layer_name:component1,component2,component3"
                   (e.g., "Ingestion:Kafka,Kinesis;Processing:Spark,Flink;Storage:S3,Delta Lake")

    Returns:
        Path to generated diagram file and confirmation message

    Example:
        create_architecture_diagram(
            "Data Lakehouse Architecture",
            "Sources:Applications,IoT,Databases;Ingestion:Kafka,Airflow;Storage:S3,Delta Lake;Processing:Spark,Presto;Serving:BI Tools,ML Models"
        )
    """
    # Parse layers
    layers = []
    for layer_str in layers_str.split(';'):
        if ':' in layer_str:
            layer_parts = layer_str.split(':')
            layer_name = layer_parts[0].strip()
            components = [c.strip() for c in layer_parts[1].split(',')]

            layers.append({
                'name': layer_name,
                'components': components
            })

    # Generate diagram
    generator = DrawIODiagramGenerator()
    filepath = generator.create_architecture_diagram(title, layers)

    return f"✅ Architecture diagram created successfully!\n\nFile: {filepath}\n\nThe diagram shows {title} with {len(layers)} layers and can be opened in DrawIO (diagrams.net)."
