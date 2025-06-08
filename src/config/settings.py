"""
Configuration settings for the OVN Explorer application.
"""

import os
import yaml
import logging

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    'ovn_connection': {
        'namespace': 'openshift-ovn-kubernetes',
        'label_selector': 'app=ovnkube-node',
        'container': 'nbdb',
        'kubeconfig': None,  # Use default kubeconfig if None
        'cache_dir': None,   # Use default cache directory if None
        'load_cache_on_startup': True,  # Load cached data on startup
    },
    'gui': {
        'theme': 'light',
        'window_size': [1024, 768],
        'auto_refresh': False,  # Auto-refresh data periodically
        'refresh_interval': 60,  # Refresh interval in seconds
    },
    'data': {
        'cache_enabled': True,  # Enable data caching
        'cache_expiry': 3600,   # Cache expiry time in seconds
    },
    'visualization': {
        'node_size': 800,
        'edge_width': 2,
        'font_size': 10,
    },
    'logging': {
        'level': 'INFO',
    }
}

def load_config(config_path=None):
    """
    Load configuration from a YAML file.
    
    Args:
        config_path (str, optional): Path to the configuration file.
            If None, looks for config.yaml in the user's home directory
            and the application directory.
    
    Returns:
        dict: Configuration dictionary with default values merged with
            values from the configuration file.
    """
    config = DEFAULT_CONFIG.copy()
    
    # Define potential config file locations
    if config_path is None:
        potential_paths = [
            os.path.expanduser('~/.ovn_explorer/config.yaml'),
            os.path.join(os.path.dirname(__file__), '..', '..', 'config.yaml')
        ]
    else:
        potential_paths = [config_path]
    
    # Try to load config from one of the potential paths
    for path in potential_paths:
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    user_config = yaml.safe_load(f)
                    if user_config:
                        # Merge user config with default config
                        _deep_update(config, user_config)
                logger.info(f"Loaded configuration from {path}")
                break
            except Exception as e:
                logger.warning(f"Failed to load configuration from {path}: {e}")
    
    return config

def _deep_update(d, u):
    """
    Recursively update a dictionary with another dictionary.
    
    Args:
        d (dict): Dictionary to update
        u (dict): Dictionary with updates
    
    Returns:
        dict: Updated dictionary
    """
    for k, v in u.items():
        if isinstance(v, dict) and k in d and isinstance(d[k], dict):
            _deep_update(d[k], v)
        else:
            d[k] = v
    return d

def save_config(config, config_path=None):
    """
    Save configuration to a YAML file.
    
    Args:
        config (dict): Configuration dictionary
        config_path (str, optional): Path to save the configuration file.
            If None, saves to ~/.ovn_explorer/config.yaml
    
    Returns:
        bool: True if successful, False otherwise
    """
    if config_path is None:
        config_path = os.path.expanduser('~/.ovn_explorer/config.yaml')
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    
    try:
        with open(config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)
        logger.info(f"Saved configuration to {config_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to save configuration to {config_path}: {e}")
        return False
