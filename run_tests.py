#!/usr/bin/env python3
"""
Test runner for OVN Explorer.

This script discovers and runs all tests in the project.
"""

import unittest
import sys
import os

def run_tests():
    """Discover and run all tests."""
    # Add the src directory to the Python path
    src_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src')
    sys.path.insert(0, src_dir)
    
    # Discover tests
    test_loader = unittest.TestLoader()
    test_suite = test_loader.discover('tests', pattern='test_*.py')
    
    # Run tests
    test_runner = unittest.TextTestRunner(verbosity=2)
    result = test_runner.run(test_suite)
    
    # Return exit code based on test result
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(run_tests())
