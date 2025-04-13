#!/usr/bin/env python3
"""
Script to copy template configuration files to actual configuration files
"""

import os
import shutil
import json
import sys
from pathlib import Path

def setup_config():
    """Create configuration files from templates if they don't exist"""
    # Find the config directory
    project_root = Path(__file__).parent.parent
    config_dir = project_root / "config"
    
    # Create config directory if it doesn't exist
    if not config_dir.exists():
        config_dir.mkdir(parents=True)
    
    # Setup server config
    server_template = config_dir / "server_config.template.json"
    server_config = config_dir / "server_config.json"
    
    if not server_config.exists() and server_template.exists():
        print(f"Creating server configuration file: {server_config}")
        shutil.copy(server_template, server_config)
    
    # Setup client config
    client_template = config_dir / "client_config.template.json"
    client_config = config_dir / "client_config.json"
    
    if not client_config.exists() and client_template.exists():
        print(f"Creating client configuration file: {client_config}")
        shutil.copy(client_template, client_config)
    
    print("Configuration setup complete.")
    print("You can now edit the configuration files in the config directory.")

if __name__ == "__main__":
    setup_config()
