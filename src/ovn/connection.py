"""
OVN Connection module for connecting to the OVN northbound database.
"""

import logging
import subprocess
import json
from typing import Optional, List, Dict, Any, Type, Union, Tuple

from kubernetes import client, config
from kubernetes.stream import stream

from .models import (
    OVNResource, OVNCache, LogicalSwitch, LogicalRouter, 
    LogicalRouterPort, LogicalSwitchPort, LoadBalancer,
    ACL, AddressSet, DHCPOptions, QoS, NAT
)

logger = logging.getLogger(__name__)

class OVNConnection:
    """
    Class for connecting to the OVN northbound database and executing commands.
    """
    
    def __init__(self, connection_config: Dict[str, Any]):
        """
        Initialize the OVN connection.
        
        Args:
            connection_config (dict): Configuration for the OVN connection.
                Should contain:
                - namespace: Namespace where OVN pods are running
                - label_selector: Label selector for OVN pods
                - container: Container name for the northbound database
                - kubeconfig: Path to kubeconfig file (optional)
                - cache_dir: Directory to store cached data (optional)
                - load_cache_on_startup: Whether to load cached data on startup (optional)
        """
        self.namespace = connection_config.get('namespace', 'openshift-ovn-kubernetes')
        self.label_selector = connection_config.get('label_selector', 'app=ovnkube-node')
        self.container = connection_config.get('container', 'nbdb')
        self.kubeconfig = connection_config.get('kubeconfig')
        self.node_name = connection_config.get('node_name')
        self.cache_dir = connection_config.get('cache_dir')
        self.load_cache_on_startup = connection_config.get('load_cache_on_startup', True)
        
        # Initialize cache
        self.cache = OVNCache(self.cache_dir)
        
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
        
        # Initialize Kubernetes client
        self._init_kubernetes_client()
        
        # Load cached data if configured
        if self.load_cache_on_startup:
            self.load_cached_data()
        
    def _init_kubernetes_client(self):
        """Initialize the Kubernetes client."""
        try:
            if self.kubeconfig:
                config.load_kube_config(config_file=self.kubeconfig)
            else:
                # Try loading from default locations
                try:
                    config.load_kube_config()
                except config.config_exception.ConfigException:
                    # If running inside a pod
                    config.load_incluster_config()
            
            self.core_v1_api = client.CoreV1Api()
            logger.info("Kubernetes client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Kubernetes client: {e}")
            raise
    
    def find_nbdb_pod(self) -> Optional[str]:
        """
        Find the northbound database pod.
        
        Returns:
            str: Name of the northbound database pod, or None if not found
        """
        try:
            # Build the label selector
            label_selector = self.label_selector
            
            # Get pods matching the label selector
            pods = self.core_v1_api.list_namespaced_pod(
                namespace=self.namespace,
                label_selector=label_selector
            )
            
            if not pods.items:
                logger.warning(f"No pods found with label selector '{label_selector}' in namespace '{self.namespace}'")
                return None
            
            # If node name is specified, find pod on that node
            if self.node_name:
                for pod in pods.items:
                    if pod.spec.node_name == self.node_name:
                        logger.info(f"Found pod '{pod.metadata.name}' on node '{self.node_name}'")
                        return pod.metadata.name
                
                logger.warning(f"No pod found on node '{self.node_name}', using first available pod")
            
            # Use the first pod if no specific node is requested or no pod found on the specified node
            pod_name = pods.items[0].metadata.name
            logger.info(f"Using pod '{pod_name}'")
            return pod_name
        
        except Exception as e:
            logger.error(f"Error finding northbound database pod: {e}")
            return None
    
    def execute_command(self, command: List[str]) -> Optional[str]:
        """
        Execute a command in the northbound database container.
        
        Args:
            command (list): Command to execute as a list of strings
        
        Returns:
            str: Command output, or None if execution failed
        """
        pod_name = self.find_nbdb_pod()
        if not pod_name:
            logger.error("Failed to find northbound database pod")
            return None
        
        try:
            logger.info(f"Executing command in pod '{pod_name}', container '{self.container}': {' '.join(command)}")
            
            # Execute the command in the pod
            resp = stream(
                self.core_v1_api.connect_get_namespaced_pod_exec,
                pod_name,
                self.namespace,
                container=self.container,
                command=command,
                stderr=True,
                stdin=False,
                stdout=True,
                tty=False
            )
            
            return resp
        
        except Exception as e:
            logger.error(f"Error executing command in pod: {e}")
            return None
    
    def load_cached_data(self):
        """Load all cached data."""
        cached_data = self.cache.load_cached_data()
        logger.info(f"Loaded cached data: {', '.join(f'{len(resources)} {res_type}' for res_type, resources in cached_data.items())}")
    
    def get_resources(self, resource_class: Type[OVNResource], use_cache: bool = False) -> List[OVNResource]:
        """
        Get resources of a specific type.
        
        Args:
            resource_class: Resource class to get
            use_cache: Whether to use cached data if available
            
        Returns:
            List of resources
        """
        resource_type = resource_class.resource_type
        
        # Check cache first if requested
        if use_cache and resource_type in self.cache.resources and self.cache.resources[resource_type]:
            logger.info(f"Using cached {resource_type} data")
            return self.cache.resources[resource_type]
        
        # Get command to list resources
        command = resource_class.list_resources_command()
        
        # Execute command
        output = self.execute_command(command)
        if not output:
            logger.warning(f"No output from {' '.join(command)}")
            return []
        
        # Cache the raw output regardless of parsing success
        self.cache.cache_json_data(resource_type, output)
        
        # Parse output
        resources = []
        
        # First try to parse as JSON if supported
        if resource_class.json_supported:
            try:
                resources = resource_class.from_json(output)
                logger.info(f"Successfully parsed {resource_type} data as JSON")
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse {resource_type} data as JSON: {e}")
                logger.info(f"Falling back to text parsing for {resource_type}")
                # Fall back to text parsing
                try:
                    resources = resource_class.from_text(output)
                    logger.info(f"Successfully parsed {resource_type} data as text")
                except Exception as text_error:
                    logger.error(f"Error parsing {resource_type} data as text: {text_error}")
                    logger.debug(f"Raw output: {output[:200]}...")  # Log first 200 chars of output
                    return []
        else:
            # Parse as text directly
            try:
                resources = resource_class.from_text(output)
                logger.info(f"Successfully parsed {resource_type} data as text")
            except Exception as e:
                logger.error(f"Error parsing {resource_type} data as text: {e}")
                logger.debug(f"Raw output: {output[:200]}...")  # Log first 200 chars of output
                return []
        
        # Update cache with the parsed resources
        self.cache.update_resources(resource_type, resources)
        
        return resources
    
    def get_router_ports(self, router: LogicalRouter) -> List[LogicalRouterPort]:
        """
        Get ports for a specific router.
        
        Args:
            router: Router to get ports for
            
        Returns:
            List of router ports
        """
        # Get command to list router ports
        command = LogicalRouterPort.list_for_router(router.uuid)
        
        # Execute command
        output = self.execute_command(command)
        if not output:
            return []
        
        # Parse output
        try:
            # Try to parse as JSON first (though lrp-list doesn't support JSON format)
            if '--format=json' in command:
                ports = LogicalRouterPort.from_json(output)
            else:
                # Parse as text
                ports = LogicalRouterPort.from_text(output, router.uuid)
            
            # Update router's ports
            router.ports = ports
            
            return ports
        except Exception as e:
            logger.error(f"Error parsing router ports: {e}")
            return []
    
    def get_logical_routers(self) -> List[LogicalRouter]:
        """
        Get all logical routers from the OVN northbound database.
        
        Returns:
            list: List of logical routers
        """
        routers = self.get_resources(LogicalRouter)
        
        # Get ports for each router
        for router in routers:
            self.get_router_ports(router)
        
        return routers
    
    def get_logical_switches(self) -> List[LogicalSwitch]:
        """
        Get all logical switches from the OVN northbound database.
        
        Returns:
            list: List of logical switches
        """
        return self.get_resources(LogicalSwitch)
    
    def get_load_balancers(self) -> List[LoadBalancer]:
        """
        Get all load balancers from the OVN northbound database.
        
        Returns:
            list: List of load balancers
        """
        return self.get_resources(LoadBalancer)
    
    def get_logical_switch_ports(self) -> List[LogicalSwitchPort]:
        """
        Get all logical switch ports from the OVN northbound database.
        
        Returns:
            list: List of logical switch ports
        """
        return self.get_resources(LogicalSwitchPort)
    
    def get_all_components(self) -> Dict[str, List[OVNResource]]:
        """
        Get all OVN components.
        
        Returns:
            dict: Dictionary with all OVN components
        """
        return {
            'logical_routers': self.get_logical_routers(),
            'logical_switches': self.get_logical_switches(),
            'load_balancers': self.get_load_balancers(),
            'logical_switch_ports': self.get_logical_switch_ports(),
        }
    
    def refresh_all_data(self) -> Dict[str, List[OVNResource]]:
        """
        Refresh all OVN data.
        
        Returns:
            dict: Dictionary with all refreshed OVN components
        """
        logger.info("Refreshing all OVN data")
        
        components = {}
        
        # Refresh each resource type
        for resource_type, resource_class in self.resource_classes.items():
            try:
                resources = self.get_resources(resource_class)
                
                # Special handling for routers to get their ports
                if resource_type == 'logical_router':
                    for router in resources:
                        self.get_router_ports(router)
                
                components[resource_type] = resources
                logger.info(f"Refreshed {len(resources)} {resource_type} resources")
            except Exception as e:
                logger.error(f"Error refreshing {resource_type} data: {e}")
                components[resource_type] = []
        
        return components
