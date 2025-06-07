"""
Network visualization for OVN components.
"""

import logging
from typing import Dict, Any, List, Optional

import networkx as nx
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox, QLabel
from PyQt6.QtCore import Qt, pyqtSlot

logger = logging.getLogger(__name__)

class NetworkView(QWidget):
    """Widget for visualizing OVN network components."""
    
    def __init__(self):
        """Initialize the network view."""
        super().__init__()
        
        self.components = {}
        self.graph = nx.Graph()
        self.highlighted_component = None
        
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the user interface."""
        # Main layout
        layout = QVBoxLayout(self)
        
        # Controls layout
        controls_layout = QHBoxLayout()
        
        # Layout algorithm selection
        self.layout_label = QLabel("Layout:")
        controls_layout.addWidget(self.layout_label)
        
        self.layout_combo = QComboBox()
        self.layout_combo.addItems(["spring", "circular", "kamada_kawai", "spectral", "shell"])
        self.layout_combo.setCurrentText("spring")
        self.layout_combo.currentTextChanged.connect(self._on_layout_changed)
        controls_layout.addWidget(self.layout_combo)
        
        # Zoom controls
        self.zoom_in_button = QPushButton("Zoom In")
        self.zoom_in_button.clicked.connect(self._on_zoom_in)
        controls_layout.addWidget(self.zoom_in_button)
        
        self.zoom_out_button = QPushButton("Zoom Out")
        self.zoom_out_button.clicked.connect(self._on_zoom_out)
        controls_layout.addWidget(self.zoom_out_button)
        
        self.reset_view_button = QPushButton("Reset View")
        self.reset_view_button.clicked.connect(self._on_reset_view)
        controls_layout.addWidget(self.reset_view_button)
        
        controls_layout.addStretch()
        
        layout.addLayout(controls_layout)
        
        # Matplotlib figure
        self.figure = Figure(figsize=(5, 4), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)
        
        # Initialize the plot
        self.ax = self.figure.add_subplot(111)
        self.ax.set_title("OVN Network Visualization")
        self.ax.axis('off')
        
        # Draw empty graph
        self._draw_graph()
    
    def update_visualization(self, components: Dict[str, List[Dict[str, Any]]]):
        """
        Update the visualization with new components.
        
        Args:
            components: Dictionary of OVN components
        """
        self.components = components
        self._build_graph()
        self._draw_graph()
    
    def _build_graph(self):
        """Build the NetworkX graph from OVN components."""
        # Create a new graph
        self.graph = nx.Graph()
        
        # Add nodes for logical routers
        for router in self.components.get('logical_routers', []):
            router_name = router.get('name', 'Unknown Router')
            self.graph.add_node(router_name, type='router', data=router)
            
            # Add router ports
            for port in router.get('ports', []):
                port_name = port.get('name', 'Unknown Port')
                self.graph.add_node(port_name, type='router_port', data=port)
                self.graph.add_edge(router_name, port_name)
        
        # Add nodes for logical switches
        for switch in self.components.get('logical_switches', []):
            switch_name = switch.get('name', 'Unknown Switch')
            self.graph.add_node(switch_name, type='switch', data=switch)
            
            # Connect switches to ports (simplified - in a real app, you'd need to determine actual connections)
            # This is just a placeholder for demonstration
            for port in self.components.get('ports', []):
                port_name = port.get('name', 'Unknown Port')
                if port_name.startswith(switch_name):
                    self.graph.add_node(port_name, type='port', data=port)
                    self.graph.add_edge(switch_name, port_name)
        
        # Add nodes for load balancers
        for lb in self.components.get('load_balancers', []):
            lb_name = lb.get('name', 'Unknown LB')
            self.graph.add_node(lb_name, type='load_balancer', data=lb)
            
            # Connect load balancers to switches (simplified - in a real app, you'd need to determine actual connections)
            # This is just a placeholder for demonstration
            for switch in self.components.get('logical_switches', []):
                switch_name = switch.get('name', 'Unknown Switch')
                if lb_name.startswith(switch_name):
                    self.graph.add_edge(lb_name, switch_name)
    
    def _draw_graph(self):
        """Draw the NetworkX graph."""
        self.ax.clear()
        
        if not self.graph.nodes:
            self.ax.text(0.5, 0.5, "No OVN components to display", 
                         horizontalalignment='center', verticalalignment='center')
            self.ax.axis('off')
            self.canvas.draw()
            return
        
        # Get the current layout algorithm
        layout_algorithm = self.layout_combo.currentText()
        
        # Calculate node positions
        if layout_algorithm == "spring":
            pos = nx.spring_layout(self.graph)
        elif layout_algorithm == "circular":
            pos = nx.circular_layout(self.graph)
        elif layout_algorithm == "kamada_kawai":
            pos = nx.kamada_kawai_layout(self.graph)
        elif layout_algorithm == "spectral":
            pos = nx.spectral_layout(self.graph)
        elif layout_algorithm == "shell":
            pos = nx.shell_layout(self.graph)
        else:
            pos = nx.spring_layout(self.graph)
        
        # Node colors based on type
        node_colors = []
        for node in self.graph.nodes:
            node_type = self.graph.nodes[node].get('type', 'unknown')
            if node_type == 'router':
                node_colors.append('red')
            elif node_type == 'switch':
                node_colors.append('blue')
            elif node_type == 'load_balancer':
                node_colors.append('green')
            elif node_type == 'port' or node_type == 'router_port':
                node_colors.append('orange')
            else:
                node_colors.append('gray')
        
        # Draw nodes
        nx.draw_networkx_nodes(
            self.graph, pos, 
            node_color=node_colors, 
            node_size=700,
            alpha=0.8,
            ax=self.ax
        )
        
        # Draw edges
        nx.draw_networkx_edges(
            self.graph, pos, 
            width=2, 
            alpha=0.5,
            ax=self.ax
        )
        
        # Draw labels
        nx.draw_networkx_labels(
            self.graph, pos, 
            font_size=10, 
            font_family='sans-serif',
            ax=self.ax
        )
        
        # Highlight selected component if any
        if self.highlighted_component:
            component_type = self.highlighted_component.get('type')
            component_data = self.highlighted_component.get('data', {})
            component_name = component_data.get('name', 'Unknown')
            
            if component_name in self.graph.nodes:
                nx.draw_networkx_nodes(
                    self.graph, pos,
                    nodelist=[component_name],
                    node_color='yellow',
                    node_size=800,
                    alpha=1.0,
                    ax=self.ax
                )
        
        # Set title and turn off axis
        self.ax.set_title("OVN Network Visualization")
        self.ax.axis('off')
        
        # Draw the canvas
        self.canvas.draw()
    
    def highlight_component(self, component_data: Dict[str, Any]):
        """
        Highlight a component in the visualization.
        
        Args:
            component_data: Data for the component to highlight
        """
        self.highlighted_component = component_data
        self._draw_graph()
    
    @pyqtSlot(str)
    def _on_layout_changed(self, layout: str):
        """
        Handle layout algorithm change.
        
        Args:
            layout: New layout algorithm
        """
        self._draw_graph()
    
    @pyqtSlot()
    def _on_zoom_in(self):
        """Handle zoom in button click."""
        self.ax.set_xlim(self.ax.get_xlim()[0] * 0.9, self.ax.get_xlim()[1] * 0.9)
        self.ax.set_ylim(self.ax.get_ylim()[0] * 0.9, self.ax.get_ylim()[1] * 0.9)
        self.canvas.draw()
    
    @pyqtSlot()
    def _on_zoom_out(self):
        """Handle zoom out button click."""
        self.ax.set_xlim(self.ax.get_xlim()[0] * 1.1, self.ax.get_xlim()[1] * 1.1)
        self.ax.set_ylim(self.ax.get_ylim()[0] * 1.1, self.ax.get_ylim()[1] * 1.1)
        self.canvas.draw()
    
    @pyqtSlot()
    def _on_reset_view(self):
        """Handle reset view button click."""
        self._draw_graph()
