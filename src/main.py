#!/usr/bin/env python3
"""
OVN Explorer - A graphical application for exploring Open Virtual Networks.

This application connects to a northbound database pod and visualizes
OVN components such as Logical Routers, Logical Switches, Load Balancers, and Ports.
"""

import sys
import logging
from PyQt6.QtWidgets import QApplication

from src.gui.main_window import MainWindow
from src.ovn.connection import OVNConnection
from src.config.settings import load_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Main entry point for the application."""
    try:
        # Configure logging
        config = load_config()
        logging_level = getattr(logging, config['logging']['level'], logging.INFO)
        logging.getLogger().setLevel(logging_level)
        
        # Initialize OVN connection with cache settings
        ovn_connection = OVNConnection(config['ovn_connection'])
        
        # Start the GUI application
        app = QApplication(sys.argv)
        window = MainWindow(ovn_connection)
        window.show()
        
        # Display a message if cache was loaded
        if config['ovn_connection'].get('load_cache_on_startup', True):
            logger.info("Loaded cached OVN data at startup")
        
        sys.exit(app.exec())
    except Exception as e:
        logger.error(f"Application error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
