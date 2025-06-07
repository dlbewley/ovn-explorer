#!/usr/bin/env python3
"""
OVN Explorer - Entry point script.

This script serves as the entry point for the OVN Explorer application.
It sets up the Python path and launches the application.
"""

import os
import sys
import logging

# Add the src directory to the Python path
src_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src')
sys.path.insert(0, src_dir)

# Import the main module
from main import main

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run the application
    main()
