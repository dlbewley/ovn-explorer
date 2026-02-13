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
        
        # Dictionary to store port information for later connection analysis
        switch_ports = {}  # key: switch name, value: list of ports
        router_ports = {}  # key: router name, value: list of ports
        all_ports = {}     # key: port name, value: port data
        
        # Add nodes for logical routers
        for router in self.components.get('logical_routers', []):
            router_name = router.name if hasattr(router, 'name') else router.get('name', 'Unknown Router')
            self.graph.add_node(router_name, type='router', data=router)
            router_ports[router_name] = []
            
            # Add router ports
            if hasattr(router, 'ports'):
                for port in router.ports:
                    port_name = port.name if hasattr(port, 'name') else port.get('name', 'Unknown Port')
                    self.graph.add_node(port_name, type='router_port', data=port)
                    self.graph.add_edge(router_name, port_name)
                    router_ports[router_name].append(port)
                    all_ports[port_name] = port
            elif isinstance(router, dict) and 'ports' in router:
                for port in router.get('ports', []):
                    port_name = port.get('name', 'Unknown Port')
                    self.graph.add_node(port_name, type='router_port', data=port)
                    self.graph.add_edge(router_name, port_name)
                    router_ports[router_name].append(port)
                    all_ports[port_name] = port
        
        # Add standalone logical router ports (if any)
        for port in self.components.get('logical_router_ports', []):
            port_name = port.name if hasattr(port, 'name') else port.get('name', 'Unknown Port')
            # Only add if not already added through a router
            if port_name not in self.graph.nodes:
                self.graph.add_node(port_name, type='router_port', data=port)
                all_ports[port_name] = port
                
                # If the port has a router reference, connect it
                router_ref = port.router if hasattr(port, 'router') else port.get('router', '')
                if router_ref:
                    # Find the router by UUID or name
                    for router in self.components.get('logical_routers', []):
                        router_uuid = router.uuid if hasattr(router, 'uuid') else router.get('uuid', '')
                        router_name = router.name if hasattr(router, 'name') else router.get('name', '')
                        if router_uuid == router_ref or router_name == router_ref:
                            router_name = router.name if hasattr(router, 'name') else router.get('name', 'Unknown Router')
                            self.graph.add_edge(router_name, port_name)
                            if router_name not in router_ports:
                                router_ports[router_name] = []
                            router_ports[router_name].append(port)
                            break
        
        # Add nodes for logical switches
        for switch in self.components.get('logical_switches', []):
            switch_name = switch.name if hasattr(switch, 'name') else switch.get('name', 'Unknown Switch')
            self.graph.add_node(switch_name, type='switch', data=switch)
            switch_ports[switch_name] = []
            
            # Get switch ports from the switch's ports attribute if available
            switch_port_refs = []
            if hasattr(switch, 'ports'):
                switch_port_refs = switch.ports
            elif isinstance(switch, dict) and 'ports' in switch:
                switch_port_refs = switch.get('ports', [])
            
            # Connect switch to its ports
            for port in self.components.get('logical_switch_ports', []):
                port_name = port.name if hasattr(port, 'name') else port.get('name', 'Unknown Port')
                port_uuid = port.uuid if hasattr(port, 'uuid') else port.get('uuid', '')
                
                # Check if this port belongs to the switch
                port_switch = port.switch if hasattr(port, 'switch') else port.get('switch', '')
                
                # Add the port if it belongs to this switch or has a matching name prefix
                if (port_uuid in switch_port_refs or 
                    port_switch == switch_name or 
                    port_switch == switch.uuid if hasattr(switch, 'uuid') else switch.get('uuid', '') or
                    port_name.startswith(switch_name)):
                    
                    self.graph.add_node(port_name, type='port', data=port)
                    self.graph.add_edge(switch_name, port_name)
                    switch_ports[switch_name].append(port)
                    all_ports[port_name] = port
        
        # Add nodes for load balancers
        for lb in self.components.get('load_balancers', []):
            lb_name = lb.name if hasattr(lb, 'name') else lb.get('name', 'Unknown LB')
            self.graph.add_node(lb_name, type='load_balancer', data=lb)
            
            # Connect load balancers to switches (simplified - in a real app, you'd need to determine actual connections)
            for switch in self.components.get('logical_switches', []):
                switch_name = switch.name if hasattr(switch, 'name') else switch.get('name', 'Unknown Switch')
                if lb_name.startswith(switch_name):
                    self.graph.add_edge(lb_name, switch_name)
        
        # Add nodes for port groups
        for pg in self.components.get('port_groups', []):
            pg_name = pg.name if hasattr(pg, 'name') else pg.get('name', 'Unknown Port Group')
            self.graph.add_node(pg_name, type='port_group', data=pg)
            
            # Connect port groups to their ports
            ports = pg.ports if hasattr(pg, 'ports') else pg.get('ports', [])
            for port_ref in ports:
                # Find the port in logical switch ports
                for port in self.components.get('logical_switch_ports', []):
                    port_uuid = port.uuid if hasattr(port, 'uuid') else port.get('uuid', '')
                    if port_uuid == port_ref:
                        port_name = port.name if hasattr(port, 'name') else port.get('name', 'Unknown Port')
                        self.graph.add_edge(pg_name, port_name)
        
        # Add nodes for chassis
        for chassis in self.components.get('chassis', []):
            chassis_name = chassis.name if hasattr(chassis, 'name') else chassis.get('name', 'Unknown Chassis')
            hostname = chassis.hostname if hasattr(chassis, 'hostname') else chassis.get('hostname', '')
            if hostname:
                chassis_name = hostname  # Use hostname for better readability
            self.graph.add_node(chassis_name, type='chassis', data=chassis)
        
        # Add nodes for meters
        for meter in self.components.get('meters', []):
            meter_name = meter.name if hasattr(meter, 'name') else meter.get('name', 'Unknown Meter')
            self.graph.add_node(meter_name, type='meter', data=meter)
        
        # Add nodes for multicast groups
        for group in self.components.get('multicast_groups', []):
            group_name = group.name if hasattr(group, 'name') else group.get('name', 'Unknown Group')
            address = group.address if hasattr(group, 'address') else group.get('address', '')
            if address:
                group_name = f"{group_name} ({address})"
            self.graph.add_node(group_name, type='multicast_group', data=group)
            
            # Connect multicast groups to their ports
            ports = group.ports if hasattr(group, 'ports') else group.get('ports', [])
            for port_ref in ports:
                # Find the port in logical switch ports
                for port in self.components.get('logical_switch_ports', []):
                    port_uuid = port.uuid if hasattr(port, 'uuid') else port.get('uuid', '')
                    if port_uuid == port_ref:
                        port_name = port.name if hasattr(port, 'name') else port.get('name', 'Unknown Port')
                        self.graph.add_edge(group_name, port_name)
        
        # Add nodes for gateways
        for gateway in self.components.get('gateways', []):
            gateway_name = gateway.name if hasattr(gateway, 'name') else gateway.get('name', 'Unknown Gateway')
            self.graph.add_node(gateway_name, type='gateway', data=gateway)
            
            # Connect gateways to their router ports
            router_port = gateway.router_port if hasattr(gateway, 'router_port') else gateway.get('router_port', '')
            if router_port:
                # Find the port in logical router ports
                for port in self.components.get('logical_router_ports', []):
                    port_name = port.name if hasattr(port, 'name') else port.get('name', 'Unknown Port')
                    port_uuid = port.uuid if hasattr(port, 'uuid') else port.get('uuid', '')
                    if port_uuid == router_port or port_name == router_port:
                        self.graph.add_edge(gateway_name, port_name)
                        break
            
            # Connect gateways to their chassis
            chassis_name = gateway.chassis_name if hasattr(gateway, 'chassis_name') else gateway.get('chassis_name', '')
            if chassis_name:
                # Find the chassis
                for chassis in self.components.get('chassis', []):
                    chassis_uuid = chassis.uuid if hasattr(chassis, 'uuid') else chassis.get('uuid', '')
                    chassis_hostname = chassis.hostname if hasattr(chassis, 'hostname') else chassis.get('hostname', '')
                    if chassis_uuid == chassis_name or chassis_hostname == chassis_name:
                        chassis_display_name = chassis_hostname if chassis_hostname else chassis.name
                        self.graph.add_edge(gateway_name, chassis_display_name)
                        break
        
        # Analyze logical switch ports and logical router ports to draw edges between them
        self._connect_ports(all_ports)
    
    def _connect_ports(self, all_ports):
        """
        Analyze ports and create connections between them.
        
        Args:
            all_ports: Dictionary of all ports (key: port name, value: port data)
        """
        # Create a mapping of MAC addresses to ports
        mac_to_port = {}
        for port_name, port in all_ports.items():
            # Get MAC address
            mac = None
            if hasattr(port, 'mac'):
                mac = port.mac
            elif isinstance(port, dict):
                mac = port.get('mac', None)
            
            if mac:
                if isinstance(mac, list):
                    for m in mac:
                        mac_to_port[m] = port_name
                else:
                    mac_to_port[mac] = port_name
        
        # Create a mapping of IP addresses/networks to ports
        ip_to_port = {}
        for port_name, port in all_ports.items():
            # Get IP address/network
            network = None
            if hasattr(port, 'network'):
                network = port.network
            elif isinstance(port, dict):
                network = port.get('network', None)
            
            if network:
                if isinstance(network, list):
                    for n in network:
                        ip_to_port[n] = port_name
                else:
                    ip_to_port[network] = port_name
            
            # Also check addresses field for logical switch ports
            addresses = None
            if hasattr(port, 'addresses'):
                addresses = port.addresses
            elif isinstance(port, dict):
                addresses = port.get('addresses', None)
            
            if addresses:
                if isinstance(addresses, list):
                    for addr in addresses:
                        # Addresses might be in format "MAC IP1 IP2..."
                        parts = addr.split()
                        if len(parts) > 1:  # Has both MAC and IP
                            for ip_part in parts[1:]:
                                ip_to_port[ip_part] = port_name
                else:
                    parts = addresses.split()
                    if len(parts) > 1:  # Has both MAC and IP
                        for ip_part in parts[1:]:
                            ip_to_port[ip_part] = port_name
        
        # Connect ports based on matching MAC addresses
        for port_name, port in all_ports.items():
            # For router ports, check if they have a peer MAC that matches another port
            peer_mac = None
            if hasattr(port, 'peer_mac'):
                peer_mac = port.peer_mac
            elif isinstance(port, dict):
                peer_mac = port.get('peer_mac', None)
            
            if peer_mac and peer_mac in mac_to_port:
                peer_port = mac_to_port[peer_mac]
                if peer_port != port_name:  # Don't connect to self
                    self.graph.add_edge(port_name, peer_port, type='peer')
            
            # For logical switch ports, check if they have a router port MAC
            if hasattr(port, 'type') and port.type == 'router':
                port_mac = None
                if hasattr(port, 'mac'):
                    port_mac = port.mac
                elif isinstance(port, dict):
                    port_mac = port.get('mac', None)
                
                if port_mac and port_mac in mac_to_port:
                    router_port = mac_to_port[port_mac]
                    if router_port != port_name:  # Don't connect to self
                        self.graph.add_edge(port_name, router_port, type='router_connection')
        
        # Connect ports based on IP networks
        # This is a simplified approach - in a real implementation, you'd need to check
        # if IP addresses are in the same subnet
        for port_name, port in all_ports.items():
            network = None
            if hasattr(port, 'network'):
                network = port.network
            elif isinstance(port, dict):
                network = port.get('network', None)
            
            if network:
                # Extract network prefix (e.g., "192.168.1" from "192.168.1.1/24")
                network_prefix = None
                if '/' in network:
                    ip_part = network.split('/')[0]
                    parts = ip_part.split('.')
                    if len(parts) >= 3:  # IPv4
                        network_prefix = '.'.join(parts[:3])
                
                if network_prefix:
                    # Find other ports in the same network
                    for other_port, other_data in all_ports.items():
                        if other_port == port_name:
                            continue  # Skip self
                        
                        other_network = None
                        if hasattr(other_data, 'network'):
                            other_network = other_data.network
                        elif isinstance(other_data, dict):
                            other_network = other_data.get('network', None)
                        
                        if other_network and network_prefix in other_network:
                            self.graph.add_edge(port_name, other_port, type='network')
    
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
            elif node_type == 'port':
                node_colors.append('orange')
            elif node_type == 'router_port':
                node_colors.append('darkorange')
            elif node_type == 'port_group':
                node_colors.append('purple')
            elif node_type == 'chassis':
                node_colors.append('brown')
            elif node_type == 'meter':
                node_colors.append('cyan')
            elif node_type == 'multicast_group':
                node_colors.append('magenta')
            elif node_type == 'gateway':
                node_colors.append('darkgreen')
            elif node_type == 'connection':
                node_colors.append('darkblue')
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
            
            # Get component name
            if hasattr(component_data, 'name'):
                component_name = component_data.name
            elif isinstance(component_data, dict):
                component_name = component_data.get('name', 'Unknown')
            else:
                component_name = 'Unknown'
            
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
