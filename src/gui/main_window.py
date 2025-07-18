"""
Main window for the OVN Explorer application.
"""

import logging
from typing import Dict, Any, Optional

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QSplitter, QTreeWidget, QTreeWidgetItem, QTabWidget,
    QTextEdit, QLabel, QPushButton, QStatusBar, QToolBar,
    QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSlot, QSize, QTimer
from PyQt6.QtGui import QAction, QIcon

from ..ovn.connection import OVNConnection
from ..visualization.network_view import NetworkView

logger = logging.getLogger(__name__)

class MainWindow(QMainWindow):
    """Main window for the OVN Explorer application."""
    
    def __init__(self, ovn_connection: OVNConnection):
        """
        Initialize the main window.
        
        Args:
            ovn_connection: OVNConnection instance for interacting with OVN
        """
        super().__init__()
        
        self.ovn_connection = ovn_connection
        self.components = {}
        
        self._init_ui()
        self._create_actions()
        self._create_menus()
        self._create_toolbars()
        self._create_status_bar()
        
        self.setWindowTitle("OVN Explorer")
        self.resize(1024, 768)
        
        # Load initial data
        self.refresh_data()
    
    def _init_ui(self):
        """Initialize the user interface."""
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        
        # Create splitter for resizable panels
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)
        
        # Left panel - Component tree
        self.component_tree = QTreeWidget()
        self.component_tree.setHeaderLabels(["OVN Components"])
        self.component_tree.setMinimumWidth(250)
        self.component_tree.itemClicked.connect(self._on_component_selected)
        splitter.addWidget(self.component_tree)
        
        # Right panel - Tabs for different views
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        self.view_tabs = QTabWidget()
        
        # Network visualization tab
        self.network_view = NetworkView()
        self.view_tabs.addTab(self.network_view, "Network Visualization")
        
        # Details tab
        self.details_view = QTextEdit()
        self.details_view.setReadOnly(True)
        self.view_tabs.addTab(self.details_view, "Details")
        
        # Console tab for command output
        self.console_view = QTextEdit()
        self.console_view.setReadOnly(True)
        self.console_view.setFontFamily("Courier New")
        self.view_tabs.addTab(self.console_view, "Console")
        
        right_layout.addWidget(self.view_tabs)
        splitter.addWidget(right_panel)
        
        # Set initial splitter sizes
        splitter.setSizes([250, 750])
    
    def _create_actions(self):
        """Create actions for menus and toolbars."""
        # Refresh action
        self.refresh_action = QAction("Refresh", self)
        self.refresh_action.setStatusTip("Refresh OVN data")
        self.refresh_action.triggered.connect(self.refresh_data)
        
        # Refresh All Data action
        self.refresh_all_action = QAction("Refresh All Data", self)
        self.refresh_all_action.setStatusTip("Refresh all OVN data from the northbound database")
        self.refresh_all_action.triggered.connect(self.refresh_all_data)
        
        # Exit action
        self.exit_action = QAction("Exit", self)
        self.exit_action.setStatusTip("Exit the application")
        self.exit_action.triggered.connect(self.close)
        
        # About action
        self.about_action = QAction("About", self)
        self.about_action.setStatusTip("Show about dialog")
        self.about_action.triggered.connect(self._show_about_dialog)
    
    def _create_menus(self):
        """Create menus."""
        # File menu
        file_menu = self.menuBar().addMenu("&File")
        file_menu.addAction(self.refresh_action)
        file_menu.addSeparator()
        file_menu.addAction(self.exit_action)
        
        # Help menu
        help_menu = self.menuBar().addMenu("&Help")
        help_menu.addAction(self.about_action)
    
    def _create_toolbars(self):
        """Create toolbars."""
        # Main toolbar
        main_toolbar = QToolBar("Main Toolbar")
        main_toolbar.setIconSize(QSize(16, 16))
        self.addToolBar(main_toolbar)
        
        # Add refresh all data button with more prominence
        refresh_button = QPushButton("Refresh All Data")
        refresh_button.setToolTip("Refresh all OVN data from the northbound database")
        refresh_button.clicked.connect(self.refresh_all_data)
        main_toolbar.addWidget(refresh_button)
        
        main_toolbar.addSeparator()
        main_toolbar.addAction(self.refresh_action)
    
    def _create_status_bar(self):
        """Create status bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
    
    @pyqtSlot()
    def refresh_all_data(self):
        """Refresh all OVN data from the northbound database."""
        self.status_bar.showMessage("Refreshing all OVN data from the northbound database...")
        
        try:
            # Use the refresh_all_data method to get fresh data
            self.components = self.ovn_connection.refresh_all_data()
            
            # Update the component tree
            self._update_component_tree()
            
            # Update the network visualization
            self.network_view.update_visualization(self.components)
            
            self.status_bar.showMessage("All OVN data refreshed successfully", 3000)
        except Exception as e:
            logger.error(f"Error refreshing all OVN data: {e}")
            self.status_bar.showMessage(f"Error refreshing all OVN data: {e}", 5000)
            QMessageBox.critical(self, "Error", f"Failed to refresh all OVN data: {e}")
    
    @pyqtSlot()
    def refresh_data(self):
        """Refresh OVN data."""
        self.status_bar.showMessage("Refreshing OVN data...")
        
        try:
            # Get all components
            self.components = self.ovn_connection.get_all_components()
            
            # Update the component tree
            self._update_component_tree()
            
            # Update the network visualization
            self.network_view.update_visualization(self.components)
            
            self.status_bar.showMessage("OVN data refreshed successfully", 3000)
        except Exception as e:
            logger.error(f"Error refreshing OVN data: {e}")
            self.status_bar.showMessage(f"Error refreshing OVN data: {e}", 5000)
            QMessageBox.critical(self, "Error", f"Failed to refresh OVN data: {e}")
    
    def _update_component_tree(self):
        """Update the component tree with the latest data."""
        self.component_tree.clear()
        
        # Create top-level items for each component type
        router_item = QTreeWidgetItem(self.component_tree, ["Logical Routers"])
        switch_item = QTreeWidgetItem(self.component_tree, ["Logical Switches"])
        lb_item = QTreeWidgetItem(self.component_tree, ["Load Balancers"])
        port_item = QTreeWidgetItem(self.component_tree, ["Logical Switch Ports"])
        
        # Add logical routers
        for router in self.components.get('logical_routers', []):
            router_name = router.name if hasattr(router, 'name') else router.get('name', 'Unknown')
            router_child = QTreeWidgetItem(router_item, [router_name])
            router_child.setData(0, Qt.ItemDataRole.UserRole, {'type': 'router', 'data': router})
            
            # Add router ports as children
            if hasattr(router, 'ports'):
                for port in router.ports:
                    port_name = port.name if hasattr(port, 'name') else port.get('name', 'Unknown')
                    port_child = QTreeWidgetItem(router_child, [port_name])
                    port_child.setData(0, Qt.ItemDataRole.UserRole, {'type': 'router_port', 'data': port})
            elif isinstance(router, dict) and 'ports' in router:
                for port in router.get('ports', []):
                    port_name = port.get('name', 'Unknown')
                    port_child = QTreeWidgetItem(router_child, [port_name])
                    port_child.setData(0, Qt.ItemDataRole.UserRole, {'type': 'router_port', 'data': port})
        
        # Add logical switches
        for switch in self.components.get('logical_switches', []):
            switch_name = switch.name if hasattr(switch, 'name') else switch.get('name', 'Unknown')
            switch_child = QTreeWidgetItem(switch_item, [switch_name])
            switch_child.setData(0, Qt.ItemDataRole.UserRole, {'type': 'switch', 'data': switch})
        
        # Add load balancers
        for lb in self.components.get('load_balancers', []):
            lb_name = lb.name if hasattr(lb, 'name') else lb.get('name', 'Unknown')
            lb_child = QTreeWidgetItem(lb_item, [lb_name])
            lb_child.setData(0, Qt.ItemDataRole.UserRole, {'type': 'load_balancer', 'data': lb})
        
        # Add logical switch ports
        for port in self.components.get('logical_switch_ports', []):
            port_name = port.name if hasattr(port, 'name') else port.get('name', 'Unknown')
            port_child = QTreeWidgetItem(port_item, [port_name])
            port_child.setData(0, Qt.ItemDataRole.UserRole, {'type': 'port', 'data': port})
        
        # Expand all items
        self.component_tree.expandAll()
    
    @pyqtSlot(QTreeWidgetItem, int)
    def _on_component_selected(self, item: QTreeWidgetItem, column: int):
        """
        Handle component selection in the tree.
        
        Args:
            item: Selected tree item
            column: Selected column
        """
        # Get the item data
        item_data = item.data(0, Qt.ItemDataRole.UserRole)
        if not item_data:
            return
        
        # Update the details view
        self._update_details_view(item_data)
        
        # Highlight the selected component in the network view
        self.network_view.highlight_component(item_data)
    
    def _update_details_view(self, item_data: Dict[str, Any]):
        """
        Update the details view with the selected component's details.
        
        Args:
            item_data: Data for the selected component
        """
        component_type = item_data.get('type', 'unknown')
        component_data = item_data.get('data', {})
        
        # Get component name
        if hasattr(component_data, 'name'):
            component_name = component_data.name
        elif isinstance(component_data, dict):
            component_name = component_data.get('name', 'Unknown')
        else:
            component_name = 'Unknown'
        
        # Format the details as HTML
        details_html = f"<h2>{component_type.replace('_', ' ').title()}: {component_name}</h2>"
        details_html += "<table border='0' cellspacing='5' cellpadding='5'>"
        
        # Handle OVNResource objects
        if hasattr(component_data, 'to_dict'):
            data_dict = component_data.to_dict()
        elif isinstance(component_data, dict):
            data_dict = component_data
        else:
            data_dict = {'data': str(component_data)}
        
        for key, value in data_dict.items():
            if key in ['name', 'type']:  # Name is already in the header, type is redundant
                continue
                
            if isinstance(value, list):
                # Format lists
                list_html = "<ul>"
                for item in value:
                    if hasattr(item, 'to_dict'):
                        # Handle OVNResource objects in lists
                        item_dict = item.to_dict()
                        list_html += "<li>"
                        for k, v in item_dict.items():
                            if k not in ['name', 'type']:
                                list_html += f"{k.replace('_', ' ').title()}: {v}<br>"
                        list_html += "</li>"
                    elif isinstance(item, dict):
                        # Format dictionaries in lists
                        list_html += "<li>"
                        for k, v in item.items():
                            list_html += f"{k.replace('_', ' ').title()}: {v}<br>"
                        list_html += "</li>"
                    else:
                        list_html += f"<li>{item}</li>"
                list_html += "</ul>"
                value = list_html
            elif isinstance(value, dict):
                # Format dictionaries
                dict_html = "<ul>"
                for k, v in value.items():
                    dict_html += f"<li>{k.replace('_', ' ').title()}: {v}</li>"
                dict_html += "</ul>"
                value = dict_html
                
            details_html += f"<tr><td><b>{key.replace('_', ' ').title()}</b></td><td>{value}</td></tr>"
        
        details_html += "</table>"
        
        # Set the HTML content
        self.details_view.setHtml(details_html)
        
        # Switch to the details tab
        self.view_tabs.setCurrentIndex(1)
    
    def _show_about_dialog(self):
        """Show the about dialog."""
        QMessageBox.about(
            self,
            "About OVN Explorer",
            "OVN Explorer\n\n"
            "A graphical application for exploring Open Virtual Networks.\n\n"
            "This application connects to a northbound database pod and visualizes "
            "OVN components such as Logical Routers, Logical Switches, Load Balancers, and Ports."
        )
    
    def execute_command(self, command):
        """
        Execute an OVN command and display the output in the console.
        
        Args:
            command: Command to execute as a list of strings
        """
        self.status_bar.showMessage(f"Executing command: {' '.join(command)}...")
        
        try:
            output = self.ovn_connection.execute_command(command)
            
            # Display the output in the console
            self.console_view.append(f"> {' '.join(command)}\n")
            if output:
                self.console_view.append(output)
            else:
                self.console_view.append("No output or command failed")
            self.console_view.append("\n")
            
            # Switch to the console tab
            self.view_tabs.setCurrentIndex(2)
            
            self.status_bar.showMessage("Command executed successfully", 3000)
            return output
        except Exception as e:
            logger.error(f"Error executing command: {e}")
            self.status_bar.showMessage(f"Error executing command: {e}", 5000)
            self.console_view.append(f"Error: {e}\n")
            return None
