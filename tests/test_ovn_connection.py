"""
Tests for the OVN Connection module.
"""

import unittest
from unittest.mock import patch, MagicMock

import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from ovn.connection import OVNConnection

class TestOVNConnection(unittest.TestCase):
    """Test cases for the OVNConnection class."""
    
    @patch('ovn.connection.config')
    @patch('ovn.connection.client')
    def setUp(self, mock_client, mock_config):
        """Set up the test case."""
        # Mock the Kubernetes client
        self.mock_core_v1_api = MagicMock()
        mock_client.CoreV1Api.return_value = self.mock_core_v1_api
        
        # Create an OVNConnection instance
        self.connection = OVNConnection({
            'namespace': 'test-namespace',
            'label_selector': 'app=test-app',
            'container': 'test-container',
        })
    
    def test_init(self):
        """Test initialization of OVNConnection."""
        self.assertEqual(self.connection.namespace, 'test-namespace')
        self.assertEqual(self.connection.label_selector, 'app=test-app')
        self.assertEqual(self.connection.container, 'test-container')
        self.assertIsNone(self.connection.kubeconfig)
        self.assertIsNone(self.connection.node_name)
    
    @patch('ovn.connection.stream')
    def test_execute_command(self, mock_stream):
        """Test executing a command."""
        # Mock finding a pod
        self.connection.find_nbdb_pod = MagicMock(return_value='test-pod')
        
        # Mock the stream function
        mock_stream.return_value = 'test output'
        
        # Execute a command
        result = self.connection.execute_command(['test', 'command'])
        
        # Check the result
        self.assertEqual(result, 'test output')
        
        # Check that the stream function was called with the correct arguments
        mock_stream.assert_called_once_with(
            self.mock_core_v1_api.connect_get_namespaced_pod_exec,
            'test-pod',
            'test-namespace',
            container='test-container',
            command=['test', 'command'],
            stderr=True,
            stdin=False,
            stdout=True,
            tty=False
        )
    
    def test_find_nbdb_pod(self):
        """Test finding a northbound database pod."""
        # Mock the list_namespaced_pod function
        mock_pod = MagicMock()
        mock_pod.metadata.name = 'test-pod'
        mock_pod.spec.node_name = 'test-node'
        
        mock_pod_list = MagicMock()
        mock_pod_list.items = [mock_pod]
        
        self.mock_core_v1_api.list_namespaced_pod.return_value = mock_pod_list
        
        # Find a pod
        pod_name = self.connection.find_nbdb_pod()
        
        # Check the result
        self.assertEqual(pod_name, 'test-pod')
        
        # Check that the list_namespaced_pod function was called with the correct arguments
        self.mock_core_v1_api.list_namespaced_pod.assert_called_once_with(
            namespace='test-namespace',
            label_selector='app=test-app'
        )
    
    def test_find_nbdb_pod_with_node_name(self):
        """Test finding a northbound database pod on a specific node."""
        # Set a node name
        self.connection.node_name = 'test-node'
        
        # Mock the list_namespaced_pod function
        mock_pod1 = MagicMock()
        mock_pod1.metadata.name = 'test-pod-1'
        mock_pod1.spec.node_name = 'other-node'
        
        mock_pod2 = MagicMock()
        mock_pod2.metadata.name = 'test-pod-2'
        mock_pod2.spec.node_name = 'test-node'
        
        mock_pod_list = MagicMock()
        mock_pod_list.items = [mock_pod1, mock_pod2]
        
        self.mock_core_v1_api.list_namespaced_pod.return_value = mock_pod_list
        
        # Find a pod
        pod_name = self.connection.find_nbdb_pod()
        
        # Check the result
        self.assertEqual(pod_name, 'test-pod-2')

if __name__ == '__main__':
    unittest.main()
