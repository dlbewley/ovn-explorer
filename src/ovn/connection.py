"""
OVN Connection module for connecting to the OVN northbound database.
"""

import logging
import subprocess
from typing import Optional, List, Dict, Any

from kubernetes import client, config
from kubernetes.stream import stream

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
        """
        self.namespace = connection_config.get('namespace', 'openshift-ovn-kubernetes')
        self.label_selector = connection_config.get('label_selector', 'app=ovnkube-node')
        self.container = connection_config.get('container', 'nbdb')
        self.kubeconfig = connection_config.get('kubeconfig')
        self.node_name = connection_config.get('node_name')
        
        self._init_kubernetes_client()
        
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
    
    def get_logical_routers(self) -> List[Dict[str, Any]]:
        """
        Get all logical routers from the OVN northbound database.
        
        Returns:
            list: List of logical routers as dictionaries
        """
        output = self.execute_command(['ovn-nbctl', 'show'])
        if not output:
            return []
        
        # Parse the output to extract logical routers
        # This is a simplified example, actual parsing would be more complex
        routers = []
        current_router = None
        
        for line in output.splitlines():
            line = line.strip()
            
            if line.startswith('router '):
                if current_router:
                    routers.append(current_router)
                
                router_name = line.split('router ')[1].strip()
                current_router = {'name': router_name, 'ports': []}
            
            elif current_router and line.startswith('port '):
                port_name = line.split('port ')[1].strip()
                current_router['ports'].append({'name': port_name})
        
        # Add the last router if there is one
        if current_router:
            routers.append(current_router)
        
        return routers
    
    def get_logical_switches(self) -> List[Dict[str, Any]]:
        """
        Get all logical switches from the OVN northbound database.
        
        Returns:
            list: List of logical switches as dictionaries
        """
        output = self.execute_command(['ovn-nbctl', 'ls-list'])
        if not output:
            return []
        
        # Parse the output to extract logical switches
        switches = []
        
        for line in output.splitlines():
            line = line.strip()
            if not line:
                continue
            
            # Example line: "5b35d6ab-b7c0-4afb-887c-d8caff5fe520 (switch1)"
            parts = line.split(' ', 1)
            if len(parts) == 2:
                uuid = parts[0]
                name = parts[1].strip('()')
                switches.append({'uuid': uuid, 'name': name})
        
        return switches
    
    def get_load_balancers(self) -> List[Dict[str, Any]]:
        """
        Get all load balancers from the OVN northbound database.
        
        Returns:
            list: List of load balancers as dictionaries
        """
        output = self.execute_command(['ovn-nbctl', 'lb-list'])
        if not output:
            return []
        
        # Parse the output to extract load balancers
        load_balancers = []
        
        # Skip the header line
        lines = output.splitlines()[1:]
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Split by whitespace, but preserve quoted strings
            parts = line.split()
            if len(parts) >= 2:
                uuid = parts[0]
                name = parts[1] if len(parts) > 1 else ""
                
                load_balancers.append({
                    'uuid': uuid,
                    'name': name,
                })
        
        return load_balancers
    
    def get_ports(self) -> List[Dict[str, Any]]:
        """
        Get all ports from the OVN northbound database.
        
        Returns:
            list: List of ports as dictionaries
        """
        output = self.execute_command(['ovn-nbctl', 'lsp-list'])
        if not output:
            return []
        
        # Parse the output to extract ports
        ports = []
        
        for line in output.splitlines():
            line = line.strip()
            if not line:
                continue
            
            # Example line: "5b35d6ab-b7c0-4afb-887c-d8caff5fe520 (port1)"
            parts = line.split(' ', 1)
            if len(parts) == 2:
                uuid = parts[0]
                name = parts[1].strip('()')
                ports.append({'uuid': uuid, 'name': name})
        
        return ports
    
    def get_all_components(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get all OVN components (routers, switches, load balancers, ports).
        
        Returns:
            dict: Dictionary with all OVN components
        """
        return {
            'logical_routers': self.get_logical_routers(),
            'logical_switches': self.get_logical_switches(),
            'load_balancers': self.get_load_balancers(),
            'ports': self.get_ports(),
        }
