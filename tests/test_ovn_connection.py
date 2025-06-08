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
from ovn.models import OVNCache, LogicalSwitch, LogicalRouter

class TestOVNConnection(unittest.TestCase):
    """Test cases for the OVNConnection class."""
    
    @patch('ovn.connection.config')
    @patch('ovn.connection.client')
    @patch('ovn.connection.OVNCache')
    def setUp(self, mock_cache, mock_client, mock_config):
        """Set up the test case."""
        # Mock the Kubernetes client
        self.mock_core_v1_api = MagicMock()
        mock_client.CoreV1Api.return_value = self.mock_core_v1_api
        
        # Mock the OVNCache
        self.mock_cache = MagicMock()
        mock_cache.return_value = self.mock_cache
        
        # Create an OVNConnection instance
        self.connection = OVNConnection({
            'namespace': 'test-namespace',
            'label_selector': 'app=test-app',
            'container': 'test-container',
            'cache_dir': '/tmp/test-cache',
            'load_cache_on_startup': False,
        })
    
    def test_init(self):
        """Test initialization of OVNConnection."""
        self.assertEqual(self.connection.namespace, 'test-namespace')
        self.assertEqual(self.connection.label_selector, 'app=test-app')
        self.assertEqual(self.connection.container, 'test-container')
        self.assertIsNone(self.connection.kubeconfig)
        self.assertIsNone(self.connection.node_name)
        self.assertEqual(self.connection.cache_dir, '/tmp/test-cache')
        self.assertFalse(self.connection.load_cache_on_startup)
    
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
    
    def test_load_cached_data(self):
        """Test loading cached data."""
        # Mock the cache's load_cached_data method
        self.mock_cache.load_cached_data.return_value = {
            'logical_switch': [MagicMock()],
            'logical_router': [MagicMock()],
        }
        
        # Load cached data
        self.connection.load_cached_data()
        
        # Check that the cache's load_cached_data method was called
        self.mock_cache.load_cached_data.assert_called_once()
    
    @patch('ovn.connection.LogicalSwitch')
    def test_get_resources(self, mock_logical_switch_class):
        """Test getting resources."""
        # Mock the resource class
        mock_logical_switch_class.resource_type = 'logical_switch'
        mock_logical_switch_class.list_resources_command.return_value = ['ovn-nbctl', '--format=json', 'list', 'Logical_Switch']
        mock_logical_switch_class.json_supported = True
        
        # Mock resources
        mock_resource1 = MagicMock()
        mock_resource2 = MagicMock()
        mock_logical_switch_class.from_json.return_value = [mock_resource1, mock_resource2]
        
        # Mock execute_command
        self.connection.execute_command = MagicMock(return_value='{"test": "json"}')
        
        # Get resources
        resources = self.connection.get_resources(mock_logical_switch_class)
        
        # Check the result
        self.assertEqual(resources, [mock_resource1, mock_resource2])
        
        # Check that the execute_command method was called with the correct arguments
        self.connection.execute_command.assert_called_once_with(['ovn-nbctl', '--format=json', 'list', 'Logical_Switch'])
        
        # Check that the from_json method was called with the correct arguments
        mock_logical_switch_class.from_json.assert_called_once_with('{"test": "json"}')
        
        # Check that the cache's cache_json_data method was called with the correct arguments
        self.mock_cache.cache_json_data.assert_called_once_with('logical_switch', '{"test": "json"}')
        
        # Check that the cache's update_resources method was called with the correct arguments
        self.mock_cache.update_resources.assert_called_once_with('logical_switch', [mock_resource1, mock_resource2])
    
    def test_refresh_all_data(self):
        """Test refreshing all data."""
        # Mock the get_resources method
        self.connection.get_resources = MagicMock(return_value=[MagicMock()])
        
        # Mock the get_router_ports method
        self.connection.get_router_ports = MagicMock()
        
        # Refresh all data
        components = self.connection.refresh_all_data()
        
        # Check the result
        self.assertEqual(len(components), len(self.connection.resource_classes))
        for resource_type in self.connection.resource_classes:
            self.assertIn(resource_type, components)
            self.assertEqual(len(components[resource_type]), 1)
        
        # Check that the get_resources method was called for each resource type
        self.assertEqual(self.connection.get_resources.call_count, len(self.connection.resource_classes))
        
        # Check that the get_router_ports method was called for each router
        if 'logical_router' in self.connection.resource_classes:
            self.connection.get_router_ports.assert_called_once()

if __name__ == '__main__':
    unittest.main()
