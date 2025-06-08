"""
Tests for the OVN models module.
"""

import unittest
from unittest.mock import patch, MagicMock, mock_open
import json
import os
import tempfile
import shutil

import sys

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from ovn.models import (
    OVNResource, OVNCache, LogicalSwitch, LogicalRouter, 
    LogicalRouterPort, LogicalSwitchPort
)

class TestOVNResource(unittest.TestCase):
    """Test cases for the OVNResource class."""
    
    def test_init(self):
        """Test initialization of OVNResource."""
        data = {
            '_uuid': 'test-uuid',
            'name': 'test-name',
            'other_field': 'test-value'
        }
        resource = OVNResource(data)
        
        self.assertEqual(resource.uuid, 'test-uuid')
        self.assertEqual(resource.name, 'test-name')
        self.assertEqual(resource.raw_data, data)
    
    def test_list_resources_command(self):
        """Test generating the list resources command."""
        # Define a test resource class
        class TestResource(OVNResource):
            resource_type = 'test_resource'
            list_command = ['list', 'Test_Resource']
        
        # Test with JSON format
        command = TestResource.list_resources_command(json_format=True)
        self.assertEqual(command, ['ovn-nbctl', '--format=json', 'list', 'Test_Resource'])
        
        # Test without JSON format
        command = TestResource.list_resources_command(json_format=False)
        self.assertEqual(command, ['ovn-nbctl', 'list', 'Test_Resource'])
    
    def test_from_json_string(self):
        """Test creating resources from JSON string."""
        json_data = '[{"_uuid": "uuid1", "name": "name1"}, {"_uuid": "uuid2", "name": "name2"}]'
        resources = OVNResource.from_json(json_data)
        
        self.assertEqual(len(resources), 2)
        self.assertEqual(resources[0].uuid, 'uuid1')
        self.assertEqual(resources[0].name, 'name1')
        self.assertEqual(resources[1].uuid, 'uuid2')
        self.assertEqual(resources[1].name, 'name2')
    
    def test_from_json_list(self):
        """Test creating resources from JSON list."""
        json_data = [
            {'_uuid': 'uuid1', 'name': 'name1'},
            {'_uuid': 'uuid2', 'name': 'name2'}
        ]
        resources = OVNResource.from_json(json_data)
        
        self.assertEqual(len(resources), 2)
        self.assertEqual(resources[0].uuid, 'uuid1')
        self.assertEqual(resources[0].name, 'name1')
        self.assertEqual(resources[1].uuid, 'uuid2')
        self.assertEqual(resources[1].name, 'name2')
    
    def test_from_json_dict(self):
        """Test creating resources from JSON dict."""
        json_data = {'_uuid': 'uuid1', 'name': 'name1'}
        resources = OVNResource.from_json(json_data)
        
        self.assertEqual(len(resources), 1)
        self.assertEqual(resources[0].uuid, 'uuid1')
        self.assertEqual(resources[0].name, 'name1')
    
    def test_from_text(self):
        """Test creating resources from text."""
        # Format the text to match the expected regex pattern
        text = "12345678-1234-5678-1234-567812345678 (name1)\n87654321-8765-4321-8765-432187654321 (name2)"
        resources = OVNResource.from_text(text)
        
        self.assertEqual(len(resources), 2)
        self.assertEqual(resources[0].uuid, '12345678-1234-5678-1234-567812345678')
        self.assertEqual(resources[0].name, 'name1')
        self.assertEqual(resources[1].uuid, '87654321-8765-4321-8765-432187654321')
        self.assertEqual(resources[1].name, 'name2')
    
    def test_to_dict(self):
        """Test converting a resource to a dictionary."""
        data = {
            '_uuid': 'test-uuid',
            'name': 'test-name',
            'other_field': 'test-value'
        }
        resource = OVNResource(data)
        
        result = resource.to_dict()
        
        self.assertEqual(result['uuid'], 'test-uuid')
        self.assertEqual(result['name'], 'test-name')
        self.assertEqual(result['type'], 'ovn_resource')
        self.assertEqual(result['raw_data'], data)
        self.assertIn('last_updated', result)
    
    def test_str(self):
        """Test string representation of a resource."""
        data = {
            '_uuid': 'test-uuid',
            'name': 'test-name'
        }
        resource = OVNResource(data)
        
        self.assertEqual(str(resource), "ovn_resource: test-name (test-uuid)")


class TestLogicalSwitch(unittest.TestCase):
    """Test cases for the LogicalSwitch class."""
    
    def test_init(self):
        """Test initialization of LogicalSwitch."""
        data = {
            '_uuid': 'test-uuid',
            'name': 'test-name',
            'ports': ['port1', 'port2']
        }
        switch = LogicalSwitch(data)
        
        self.assertEqual(switch.uuid, 'test-uuid')
        self.assertEqual(switch.name, 'test-name')
        self.assertEqual(switch.ports, ['port1', 'port2'])
        self.assertEqual(switch.resource_type, 'logical_switch')


class TestLogicalRouter(unittest.TestCase):
    """Test cases for the LogicalRouter class."""
    
    def test_init(self):
        """Test initialization of LogicalRouter."""
        data = {
            '_uuid': 'test-uuid',
            'name': 'test-name'
        }
        router = LogicalRouter(data)
        
        self.assertEqual(router.uuid, 'test-uuid')
        self.assertEqual(router.name, 'test-name')
        self.assertEqual(router.ports, [])
        self.assertEqual(router.resource_type, 'logical_router')
    
    def test_to_dict(self):
        """Test converting a router to a dictionary."""
        data = {
            '_uuid': 'test-uuid',
            'name': 'test-name'
        }
        router = LogicalRouter(data)
        
        # Add a port
        port_data = {
            'uuid': 'port-uuid',
            'name': 'port-name'
        }
        port = LogicalRouterPort(port_data)
        router.ports = [port]
        
        result = router.to_dict()
        
        self.assertEqual(result['uuid'], 'test-uuid')
        self.assertEqual(result['name'], 'test-name')
        self.assertEqual(result['type'], 'logical_router')
        self.assertEqual(len(result['ports']), 1)
        self.assertEqual(result['ports'][0]['uuid'], 'port-uuid')
        self.assertEqual(result['ports'][0]['name'], 'port-name')


class TestLogicalRouterPort(unittest.TestCase):
    """Test cases for the LogicalRouterPort class."""
    
    def test_init(self):
        """Test initialization of LogicalRouterPort."""
        data = {
            'uuid': 'test-uuid',
            'name': 'test-name',
            'mac': 'test-mac',
            'network': 'test-network',
            'router': 'test-router'
        }
        port = LogicalRouterPort(data)
        
        self.assertEqual(port.uuid, 'test-uuid')
        self.assertEqual(port.name, 'test-name')
        self.assertEqual(port.mac, 'test-mac')
        self.assertEqual(port.network, 'test-network')
        self.assertEqual(port.router, 'test-router')
        self.assertEqual(port.resource_type, 'logical_router_port')
    
    def test_list_for_router(self):
        """Test generating the list ports for router command."""
        command = LogicalRouterPort.list_for_router('test-router-uuid')
        self.assertEqual(command, ['ovn-nbctl', 'lrp-list', 'test-router-uuid'])
    
    def test_from_text(self):
        """Test creating router ports from text."""
        # Format the text to match the expected regex pattern
        text = "12345678-1234-5678-1234-567812345678 (name1)\n87654321-8765-4321-8765-432187654321 (name2)"
        router_uuid = 'test-router-uuid'
        ports = LogicalRouterPort.from_text(text, router_uuid)
        
        self.assertEqual(len(ports), 2)
        self.assertEqual(ports[0].uuid, '12345678-1234-5678-1234-567812345678')
        self.assertEqual(ports[0].name, 'name1')
        self.assertEqual(ports[0].router, router_uuid)
        self.assertEqual(ports[1].uuid, '87654321-8765-4321-8765-432187654321')
        self.assertEqual(ports[1].name, 'name2')
        self.assertEqual(ports[1].router, router_uuid)


class TestOVNCache(unittest.TestCase):
    """Test cases for the OVNCache class."""
    
    def setUp(self):
        """Set up the test case."""
        # Create a temporary directory for the cache
        self.temp_dir = tempfile.mkdtemp()
        self.cache = OVNCache(self.temp_dir)
    
    def tearDown(self):
        """Clean up after the test case."""
        # Remove the temporary directory
        shutil.rmtree(self.temp_dir)
    
    def test_init(self):
        """Test initialization of OVNCache."""
        self.assertEqual(self.cache.cache_dir, self.temp_dir)
        self.assertTrue(os.path.exists(self.temp_dir))
        
        # Test with default cache directory
        with patch('os.makedirs') as mock_makedirs:
            cache = OVNCache()
            self.assertEqual(cache.cache_dir, os.path.expanduser('~/.ovn_explorer/cache'))
            mock_makedirs.assert_called_once_with(os.path.expanduser('~/.ovn_explorer/cache'), exist_ok=True)
    
    @patch('builtins.open', new_callable=mock_open)
    def test_cache_json_data(self, mock_file):
        """Test caching JSON data."""
        resource_type = 'logical_switch'
        json_data = '{"test": "json"}'
        
        self.cache.cache_json_data(resource_type, json_data)
        
        # Check that the file was opened for writing twice (once for timestamped file, once for latest)
        self.assertEqual(mock_file.call_count, 2)
        
        # Check that the JSON data was written to the file
        mock_file().write.assert_called_with(json_data)
    
    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data='{"_uuid": "test-uuid", "name": "test-name"}')
    def test_load_cached_data(self, mock_file, mock_exists):
        """Test loading cached data."""
        # Mock os.path.exists to return True for the latest file
        mock_exists.return_value = True
        
        # Load cached data
        result = self.cache.load_cached_data('logical_switch')
        
        # Check the result
        self.assertIn('logical_switch', result)
        self.assertEqual(len(result['logical_switch']), 1)
        self.assertEqual(result['logical_switch'][0].uuid, 'test-uuid')
        self.assertEqual(result['logical_switch'][0].name, 'test-name')
    
    def test_update_resources(self):
        """Test updating cached resources."""
        resource_type = 'logical_switch'
        resources = [
            LogicalSwitch({'_uuid': 'uuid1', 'name': 'name1'}),
            LogicalSwitch({'_uuid': 'uuid2', 'name': 'name2'})
        ]
        
        self.cache.update_resources(resource_type, resources)
        
        # Check that the resources were updated
        self.assertEqual(self.cache.resources[resource_type], resources)


if __name__ == '__main__':
    unittest.main()
