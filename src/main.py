#!/usr/bin/env python3
"""
OVN Explorer - A graphical application for exploring Open Virtual Networks.

This application connects to a northbound database pod and visualizes
OVN components such as Logical Routers, Logical Switches, Load Balancers, and Ports.
"""

import sys
import logging
from PyQt6.QtWidgets import QApplication

from gui.main_window import MainWindow
from ovn.connection import OVNConnection
from config.settings import load_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Main entry point for the application."""
    try:
        # Load configuration
        config = load_config()
        
        # Initialize OVN connection
        ovn_connection = OVNConnection(config['ovn_connection'])
        
        # Start the GUI application
        app = QApplication(sys.argv)
        window = MainWindow(ovn_connection)
        window.show()
        
        sys.exit(app.exec())
    except Exception as e:
        logger.error(f"Application error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
