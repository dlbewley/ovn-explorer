"""
OVN resource models for representing OVN components.
"""

import json
import logging
import os
from typing import Dict, List, Any, Optional, Union, ClassVar
from datetime import datetime
import re

logger = logging.getLogger(__name__)

class OVNResource:
    """Base class for OVN resources."""
    
    # Class variables
    resource_type: ClassVar[str] = "ovn_resource"
    command_prefix: ClassVar[str] = "ovn-nbctl"
    list_command: ClassVar[List[str]] = []
    json_supported: ClassVar[bool] = True
    
    def __init__(self, data: Dict[str, Any]):
        """
        Initialize an OVN resource.
        
        Args:
            data: Dictionary containing resource data
        """
        self.uuid = data.get('_uuid', data.get('uuid', ''))
        self.name = data.get('name', '')
        self.raw_data = data
        self.last_updated = datetime.now()
    
    @classmethod
    def list_resources_command(cls, json_format: bool = True) -> List[str]:
        """
        Get the command to list resources of this type.
        
        Args:
            json_format: Whether to request JSON output
            
        Returns:
            List of command parts
        """
        if not cls.list_command:
            raise NotImplementedError(f"list_command not defined for {cls.resource_type}")
        
        command = [cls.command_prefix]
        
        if json_format and cls.json_supported:
            command.append('--format=json')
            
        command.extend(cls.list_command)
        return command
    
    @classmethod
    def from_json(cls, json_data: Union[str, Dict, List]) -> List['OVNResource']:
        """
        Create resource instances from JSON data.
        
        Args:
            json_data: JSON data as string or parsed object
            
        Returns:
            List of resource instances
        """
        if isinstance(json_data, str):
            try:
                # Try to normalize the JSON data if it's a string
                normalized_data = json_data
                try:
                    # First try to parse as is
                    data = json.loads(json_data)
                except json.JSONDecodeError:
                    # If that fails, try to normalize it
                    logger.info(f"Attempting to normalize JSON data for {cls.resource_type}")
                    
                    # Replace single quotes with double quotes for JSON keys and string values
                    normalized_data = json_data.replace("'", '"')
                    
                    # Try to parse the normalized data
                    try:
                        data = json.loads(normalized_data)
                        logger.info(f"Successfully normalized and parsed JSON for {cls.resource_type}")
                    except json.JSONDecodeError as e:
                        # If normalization fails, try a more aggressive approach
                        logger.warning(f"Simple normalization failed: {e}")
                        
                        # Try to extract data from the structure
                        if "'data':" in normalized_data:
                            # This might be the format we've seen in the logs
                            try:
                                # Extract just the data part
                                data_start = normalized_data.find('"data":') + 8
                                data_part = normalized_data[data_start:]
                                # Find the end of the data array
                                if '"headings":' in data_part:
                                    data_end = data_part.find('"headings":')
                                    data_part = data_part[:data_end].strip()
                                    if data_part.endswith(','):
                                        data_part = data_part[:-1]
                                
                                # Try to parse just the data part
                                data = {'data': json.loads(data_part)}
                                logger.info(f"Extracted and parsed data part for {cls.resource_type}")
                            except Exception as extract_error:
                                logger.error(f"Failed to extract data part: {extract_error}")
                                raise json.JSONDecodeError(f"Failed to parse JSON after normalization: {e}", normalized_data, 0)
                        else:
                            raise json.JSONDecodeError(f"Failed to parse JSON after normalization: {e}", normalized_data, 0)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON for {cls.resource_type}: {e}")
                return []
        else:
            data = json_data
            
        if not data:
            return []
            
        # Handle the specific format we've seen in the logs
        if isinstance(data, dict) and 'data' in data and isinstance(data['data'], list):
            # This is the format with 'data' and 'headings'
            logger.info(f"Processing data in 'data' field for {cls.resource_type}")
            
            # Extract headings if available
            headings = data.get('headings', [])
            
            # Process each row in the data array
            resources = []
            for row in data['data']:
                if isinstance(row, list):
                    # Create a dictionary from the row data
                    row_data = {}
                    
                    # If we have headings, use them as keys
                    if headings and len(headings) == len(row):
                        row_data = {headings[i]: row[i] for i in range(len(headings))}
                    else:
                        # Otherwise, try to extract key-value pairs from the row
                        for i in range(0, len(row), 2):
                            if i + 1 < len(row):
                                key = row[i]
                                value = row[i + 1]
                                if isinstance(key, list) and len(key) > 0:
                                    key = key[0]  # Use the first element as the key
                                row_data[key] = value
                    
                    # Create a resource from the row data
                    resources.append(cls(row_data))
                elif isinstance(row, dict):
                    # If the row is already a dictionary, use it directly
                    resources.append(cls(row))
            
            return resources
        elif isinstance(data, list):
            return [cls(item) for item in data]
        elif isinstance(data, dict):
            return [cls(data)]
        else:
            logger.error(f"Unexpected JSON data type for {cls.resource_type}: {type(data)}")
            return []
    
    @classmethod
    def from_text(cls, text: str) -> List['OVNResource']:
        """
        Create resource instances from text output.
        
        Args:
            text: Command output text
            
        Returns:
            List of resource instances
        """
        # Default implementation - override in subclasses
        logger.warning(f"Default text parsing used for {cls.resource_type}")
        resources = []
        
        # Check if the text is empty or just whitespace
        if not text or not text.strip():
            logger.warning(f"Empty text input for {cls.resource_type}")
            return resources
            
        # Log the first 200 characters of the text for debugging
        logger.debug(f"Parsing text for {cls.resource_type}: {text[:200]}...")
            
        # Check if the text might be a table format (common in OVN output)
        if '_uuid' in text and '\n' in text and '|' in text:
            logger.info(f"Detected table format for {cls.resource_type}")
            return cls._parse_table_format(text)
            
        # Process line by line for the common "uuid (name)" format
        lines = text.strip().split('\n')
        logger.debug(f"Processing {len(lines)} lines for {cls.resource_type}")
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Try to extract UUID and name
            # Format often looks like: "uuid (name)"
            match = re.match(r'([0-9a-f-]+(?:-[0-9a-f-]+)+)\s+\(([^)]+)\)', line)
            if match:
                uuid, name = match.groups()
                logger.debug(f"Matched UUID and name: {uuid}, {name}")
                resources.append(cls({'_uuid': uuid, 'name': name}))
            else:
                # Try alternative formats
                # Some OVN commands output just the UUID
                uuid_match = re.match(r'^([0-9a-f-]+(?:-[0-9a-f-]+)+)$', line)
                if uuid_match:
                    uuid = uuid_match.group(1)
                    logger.debug(f"Matched UUID only: {uuid}")
                    resources.append(cls({'_uuid': uuid, 'name': f"Resource-{uuid[:8]}"}))
                else:
                    # Just use the whole line as name
                    logger.debug(f"Using line as name: {line}")
                    resources.append(cls({'name': line}))
                
        logger.info(f"Parsed {len(resources)} resources from text for {cls.resource_type}")
        return resources
        
    @classmethod
    def _parse_table_format(cls, text: str) -> List['OVNResource']:
        """
        Parse table-formatted text output from OVN commands.
        
        Args:
            text: Table-formatted text output
            
        Returns:
            List of resource instances
        """
        resources = []
        lines = text.strip().split('\n')
        
        # Find the header line
        header_idx = -1
        for i, line in enumerate(lines):
            if '_uuid' in line:
                header_idx = i
                break
                
        if header_idx == -1:
            logger.warning(f"Could not find header in table output for {cls.resource_type}")
            return resources
            
        # Parse the header to get column names
        header = lines[header_idx]
        columns = [col.strip() for col in header.split('|')]
        columns = [col for col in columns if col]  # Remove empty columns
        
        logger.debug(f"Found {len(columns)} columns in table header: {columns}")
        
        # Process each data row
        row_count = 0
        for i in range(header_idx + 1, len(lines)):
            line = lines[i]
            if not line.strip() or '---' in line:  # Skip separator lines
                continue
                
            # Split the line into columns
            values = [val.strip() for val in line.split('|')]
            values = [val for val in values if val]  # Remove empty values
            
            if len(values) != len(columns):
                logger.warning(f"Column count mismatch in row: {line}")
                logger.debug(f"Expected {len(columns)} columns, got {len(values)}")
                # Try to salvage what we can
                if len(values) > 0:
                    # Create a data dictionary with available values
                    data = {}
                    for j in range(min(len(columns), len(values))):
                        data[columns[j]] = values[j]
                    
                    # Ensure we have at least a UUID or name
                    if '_uuid' in data or 'name' in data:
                        resources.append(cls(data))
                        row_count += 1
                continue
                
            # Create a data dictionary
            data = {columns[j]: values[j] for j in range(len(columns))}
            resources.append(cls(data))
            row_count += 1
            
        logger.info(f"Parsed {row_count} rows from table format for {cls.resource_type}")
        return resources
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the resource to a dictionary.
        
        Returns:
            Dictionary representation of the resource
        """
        return {
            'uuid': self.uuid,
            'name': self.name,
            'type': self.resource_type,
            'raw_data': self.raw_data,
            'last_updated': self.last_updated.isoformat()
        }
    
    def __str__(self) -> str:
        """String representation of the resource."""
        return f"{self.resource_type}: {self.name} ({self.uuid})"


class LogicalSwitch(OVNResource):
    """Logical switch resource."""
    
    resource_type = "logical_switch"
    list_command = ["list", "Logical_Switch"]
    
    def __init__(self, data: Dict[str, Any]):
        """Initialize a logical switch."""
        super().__init__(data)
        self.ports = data.get('ports', [])
        

class LogicalRouter(OVNResource):
    """Logical router resource."""
    
    resource_type = "logical_router"
    list_command = ["list", "Logical_Router"]
    
    def __init__(self, data: Dict[str, Any]):
        """Initialize a logical router."""
        super().__init__(data)
        self.ports = []  # Will be populated separately
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert the router to a dictionary."""
        result = super().to_dict()
        result['ports'] = [port.to_dict() for port in self.ports]
        return result


class LogicalRouterPort(OVNResource):
    """Logical router port resource."""
    
    resource_type = "logical_router_port"
    list_command = ["list", "Logical_Router_Port"]
    
    def __init__(self, data: Dict[str, Any]):
        """Initialize a logical router port."""
        super().__init__(data)
        self.mac = data.get('mac', '')
        self.network = data.get('network', '')
        self.router = data.get('router', '')
        
    @classmethod
    def list_for_router(cls, router_uuid: str) -> List[str]:
        """
        Get command to list ports for a specific router.
        
        Args:
            router_uuid: UUID of the router
            
        Returns:
            Command to list ports for the router
        """
        return [cls.command_prefix, 'lrp-list', router_uuid]
    
    @classmethod
    def from_text(cls, text: str, router_uuid: Optional[str] = None) -> List['LogicalRouterPort']:
        """
        Create router port instances from text output.
        
        Args:
            text: Command output text
            router_uuid: UUID of the router these ports belong to
            
        Returns:
            List of router port instances
        """
        ports = []
        
        # Check if the text is empty or just whitespace
        if not text or not text.strip():
            logger.warning(f"Empty text input for {cls.resource_type}")
            return ports
            
        # Log the first 200 characters of the text for debugging
        logger.debug(f"Parsing text for {cls.resource_type}: {text[:200]}...")
        
        # Check if the text might be a table format
        if '_uuid' in text and '\n' in text and '|' in text:
            # Use the base class table parser and add router_uuid to each port
            resources = cls._parse_table_format(text)
            for resource in resources:
                resource.router = router_uuid
            return resources
            
        # Process line by line for the common "uuid (name)" format
        lines = text.strip().split('\n')
        logger.debug(f"Processing {len(lines)} lines for {cls.resource_type}")
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Format: "uuid (name)"
            match = re.match(r'([0-9a-f-]+(?:-[0-9a-f-]+)+)\s+\(([^)]+)\)', line)
            if match:
                uuid, name = match.groups()
                logger.debug(f"Matched UUID and name: {uuid}, {name}")
                ports.append(cls({
                    '_uuid': uuid, 
                    'name': name,
                    'router': router_uuid
                }))
            else:
                # Try alternative formats
                # Some OVN commands output just the UUID
                uuid_match = re.match(r'^([0-9a-f-]+(?:-[0-9a-f-]+)+)$', line)
                if uuid_match:
                    uuid = uuid_match.group(1)
                    logger.debug(f"Matched UUID only: {uuid}")
                    ports.append(cls({
                        '_uuid': uuid, 
                        'name': f"Port-{uuid[:8]}",
                        'router': router_uuid
                    }))
                
        logger.info(f"Parsed {len(ports)} router ports from text")
        return ports


class LogicalSwitchPort(OVNResource):
    """Logical switch port resource."""
    
    resource_type = "logical_switch_port"
    list_command = ["list", "Logical_Switch_Port"]
    
    def __init__(self, data: Dict[str, Any]):
        """Initialize a logical switch port."""
        super().__init__(data)
        self.type = data.get('type', '')
        self.addresses = data.get('addresses', [])
        self.switch = data.get('switch', '')


class LoadBalancer(OVNResource):
    """Load balancer resource."""
    
    resource_type = "load_balancer"
    list_command = ["list", "Load_Balancer"]
    
    def __init__(self, data: Dict[str, Any]):
        """Initialize a load balancer."""
        super().__init__(data)
        self.vips = data.get('vips', {})
        self.protocol = data.get('protocol', '')


class ACL(OVNResource):
    """Access Control List resource."""
    
    resource_type = "acl"
    list_command = ["list", "ACL"]
    
    def __init__(self, data: Dict[str, Any]):
        """Initialize an ACL."""
        super().__init__(data)
        self.direction = data.get('direction', '')
        self.priority = data.get('priority', 0)
        self.match = data.get('match', '')
        self.action = data.get('action', '')


class AddressSet(OVNResource):
    """Address set resource."""
    
    resource_type = "address_set"
    list_command = ["list", "Address_Set"]
    
    def __init__(self, data: Dict[str, Any]):
        """Initialize an address set."""
        super().__init__(data)
        self.addresses = data.get('addresses', [])


class DHCPOptions(OVNResource):
    """DHCP options resource."""
    
    resource_type = "dhcp_options"
    list_command = ["list", "DHCP_Options"]
    
    def __init__(self, data: Dict[str, Any]):
        """Initialize DHCP options."""
        super().__init__(data)
        self.cidr = data.get('cidr', '')
        self.options = data.get('options', {})


class QoS(OVNResource):
    """Quality of Service resource."""
    
    resource_type = "qos"
    list_command = ["list", "QoS"]
    
    def __init__(self, data: Dict[str, Any]):
        """Initialize a QoS entry."""
        super().__init__(data)
        self.direction = data.get('direction', '')
        self.priority = data.get('priority', 0)
        self.match = data.get('match', '')
        self.action = data.get('action', {})


class NAT(OVNResource):
    """Network Address Translation resource."""
    
    resource_type = "nat"
    list_command = ["list", "NAT"]
    
    def __init__(self, data: Dict[str, Any]):
        """Initialize a NAT entry."""
        super().__init__(data)
        self.type = data.get('type', '')
        self.external_ip = data.get('external_ip', '')
        self.logical_ip = data.get('logical_ip', '')
        self.logical_port = data.get('logical_port', '')


class OVNCache:
    """Cache for OVN resources."""
    
    def __init__(self, cache_dir: str = None):
        """
        Initialize the OVN cache.
        
        Args:
            cache_dir: Directory to store cache files
        """
        if cache_dir is None:
            cache_dir = os.path.expanduser('~/.ovn_explorer/cache')
            
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        
        # Resource type to class mapping
        self.resource_classes = {
            'logical_switch': LogicalSwitch,
            'logical_router': LogicalRouter,
            'logical_router_port': LogicalRouterPort,
            'logical_switch_port': LogicalSwitchPort,
            'load_balancer': LoadBalancer,
            'acl': ACL,
            'address_set': AddressSet,
            'dhcp_options': DHCPOptions,
            'qos': QoS,
            'nat': NAT
        }
        
        # Cache of resources by type
        self.resources = {resource_type: [] for resource_type in self.resource_classes}
        
    def cache_json_data(self, resource_type: str, json_data: str):
        """
        Cache JSON data for a resource type.
        
        Args:
            resource_type: Type of resource
            json_data: JSON data as string
        """
        # Normalize JSON data (replace single quotes with double quotes)
        normalized_data = self._normalize_json(json_data)
        
        # Save to file
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        filename = f"{resource_type}_{timestamp}.json"
        filepath = os.path.join(self.cache_dir, filename)
        
        try:
            with open(filepath, 'w') as f:
                f.write(normalized_data)
            logger.info(f"Cached {resource_type} data to {filepath}")
            
            # Also save as latest
            latest_path = os.path.join(self.cache_dir, f"{resource_type}_latest.json")
            with open(latest_path, 'w') as f:
                f.write(normalized_data)
                
        except Exception as e:
            logger.error(f"Failed to cache {resource_type} data: {e}")
    
    def _normalize_json(self, json_data: str) -> str:
        """
        Normalize JSON data by replacing single quotes with double quotes.
        
        Args:
            json_data: JSON data as string
            
        Returns:
            Normalized JSON data
        """
        try:
            # First try to parse as JSON (maybe it's already valid)
            json.loads(json_data)
            return json_data
        except json.JSONDecodeError:
            # If it fails, try to normalize it
            logger.info("Normalizing JSON data (replacing single quotes with double quotes)")
            
            # Replace single quotes with double quotes, but be careful with nested quotes
            # This is a simple approach and might not work for all cases
            normalized = json_data
            
            # Replace 'true' with "true"
            normalized = re.sub(r"'true'", '"true"', normalized)
            # Replace 'false' with "false"
            normalized = re.sub(r"'false'", '"false"', normalized)
            # Replace 'null' with "null"
            normalized = re.sub(r"'null'", '"null"', normalized)
            
            # Replace 'key' with "key" for dictionary keys
            normalized = re.sub(r"'([^']+)':", r'"\1":', normalized)
            
            # Replace 'value' with "value" for string values
            normalized = re.sub(r": '([^']+)'", r': "\1"', normalized)
            
            # Replace remaining single quotes with double quotes
            normalized = normalized.replace("'", '"')
            
            try:
                # Verify that the normalized JSON is valid
                json.loads(normalized)
                logger.info("Successfully normalized JSON data")
                return normalized
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to normalize JSON data: {e}")
                # If normalization fails, return the original data
                return json_data
    
    def load_cached_data(self, resource_type: str = None) -> Dict[str, List[OVNResource]]:
        """
        Load cached data for resources.
        
        Args:
            resource_type: Type of resource to load, or None for all
            
        Returns:
            Dictionary of resource lists by type
        """
        result = {}
        
        types_to_load = [resource_type] if resource_type else self.resource_classes.keys()
        
        for res_type in types_to_load:
            if res_type not in self.resource_classes:
                logger.warning(f"Unknown resource type: {res_type}")
                continue
                
            latest_path = os.path.join(self.cache_dir, f"{res_type}_latest.json")
            if not os.path.exists(latest_path):
                logger.info(f"No cached data for {res_type}")
                result[res_type] = []
                continue
                
            try:
                with open(latest_path, 'r') as f:
                    json_data = f.read()
                    
                resource_class = self.resource_classes[res_type]
                resources = resource_class.from_json(json_data)
                
                result[res_type] = resources
                logger.info(f"Loaded {len(resources)} {res_type} resources from cache")
                
            except Exception as e:
                logger.error(f"Failed to load cached {res_type} data: {e}")
                result[res_type] = []
                
        return result
    
    def update_resources(self, resource_type: str, resources: List[OVNResource]):
        """
        Update cached resources.
        
        Args:
            resource_type: Type of resource
            resources: List of resources
        """
        self.resources[resource_type] = resources
