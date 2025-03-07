"""
Odoo Inspector Module

This module provides functionality to inspect and analyze an Odoo installation,
including installed modules, access rights, and available endpoints.

Author: Shamlan Arshad
License: MIT
"""

import xmlrpc.client
import json
from typing import List, Dict, Any
from tabulate import tabulate
from datetime import datetime
import os
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Odoo connection parameters from environment variables
url = os.getenv('ODOO_URL', 'http://localhost:8069')
db = os.getenv('ODOO_DB', 'odoo')
username = os.getenv('ODOO_USERNAME', 'admin')
password = os.getenv('ODOO_PASSWORD', '')

# Connection URLs
common_url = f'{url}/xmlrpc/2/common'
object_url = f'{url}/xmlrpc/2/object'

class OdooInspector:
    """Class for inspecting Odoo server configuration and modules."""

    def __init__(self):
        self.url = url
        self.db = db
        self.username = username
        self.password = password
        self.uid = None
        self.models = None
        self.version_info = None
        self.context = {'lang': os.getenv('DEFAULT_LANGUAGE', 'en_US')}

    def connect(self) -> bool:
        """Establish connection with Odoo server"""
        try:
            # Connect to common interface
            common = xmlrpc.client.ServerProxy(common_url)
            
            # Get version info
            self.version_info = common.version()
            
            # Authenticate
            self.uid = common.authenticate(self.db, self.username, self.password, {})
            
            if self.uid:
                # Connect to object endpoint
                self.models = xmlrpc.client.ServerProxy(object_url)
                logger.info(f"Successfully connected to Odoo server at {self.url}")
                return True
            logger.error("Authentication failed")
            return False
        except Exception as e:
            logger.error(f"Connection error: {str(e)}")
            return False

    def get_server_info(self) -> Dict:
        """Get Odoo server information"""
        return {
            'server_version': self.version_info.get('server_version', 'Unknown'),
            'server_version_info': self.version_info.get('server_version_info', []),
            'protocol_version': self.version_info.get('protocol_version', 0),
            'user_id': self.uid
        }

    def get_installed_modules(self) -> List[Dict]:
        """Get list of installed modules"""
        if not self.uid:
            logger.warning("Not connected to Odoo server")
            return []
            
        try:
            module_fields = ['name', 'state', 'latest_version', 'shortdesc', 'summary']
            domain = [('state', '=', 'installed')]
            
            modules = self.models.execute_kw(self.db, self.uid, self.password,
                'ir.module.module',
                'search_read',
                [domain],
                {'fields': module_fields}
            )
            
            return modules
        except Exception as e:
            logger.error(f"Error fetching installed modules: {str(e)}")
            return []

    def get_model_access(self, module_name: str = None) -> List[Dict]:
        """Get access rights for models"""
        if not self.uid:
            logger.warning("Not connected to Odoo server")
            return []
            
        try:
            domain = []
            if module_name:
                domain = [('model_id.model', 'like', f'{module_name}%')]
                
            access_fields = ['name', 'model_id', 'perm_read', 'perm_write', 'perm_create', 'perm_unlink']
            
            access_rights = self.models.execute_kw(self.db, self.uid, self.password,
                'ir.model.access',
                'search_read',
                [domain],
                {'fields': access_fields}
            )
            
            return access_rights
        except Exception as e:
            logger.error(f"Error fetching model access rights: {str(e)}")
            return []

    def get_available_endpoints(self) -> List[Dict]:
        """Get available API endpoints"""
        if not self.uid:
            logger.warning("Not connected to Odoo server")
            return []
            
        try:
            model_fields = ['model', 'name', 'state', 'transient']
            
            models = self.models.execute_kw(self.db, self.uid, self.password,
                'ir.model',
                'search_read',
                [[]],
                {'fields': model_fields}
            )
            
            endpoints = []
            for model in models:
                # Get model's methods
                methods = self.models.execute_kw(self.db, self.uid, self.password,
                    model['model'],
                    'fields_get',
                    [],
                    {'attributes': ['string', 'help', 'type']}
                )
                
                endpoints.append({
                    'model': model['model'],
                    'name': model['name'],
                    'state': model['state'],
                    'is_transient': model['transient'],
                    'field_count': len(methods) if methods else 0
                })
                
            return endpoints
        except Exception as e:
            logger.error(f"Error fetching available endpoints: {str(e)}")
            return []

def main():
    """Main function to run the Odoo Inspector."""
    inspector = OdooInspector()
    
    logger.info("Connecting to Odoo server...")
    if not inspector.connect():
        logger.error("Failed to connect to Odoo server.")
        return

    # Get server information
    server_info = inspector.get_server_info()
    print("\nOdoo Server Information:")
    print("-" * 40)
    print(f"Server Version: {server_info['server_version']}")
    print(f"Protocol Version: {server_info['protocol_version']}")
    print(f"User ID: {server_info['user_id']}")

    # Get installed modules
    print("\nInstalled Modules:")
    print("-" * 40)
    modules = inspector.get_installed_modules()
    if modules:
        module_table = [[
            m['name'],
            m['latest_version'],
            m['state'],
            m.get('summary', 'No description')
        ] for m in modules]
        print(tabulate(
            module_table,
            headers=['Module', 'Version', 'State', 'Description'],
            tablefmt='grid'
        ))
    else:
        print("No modules found or error occurred.")

    # Get API endpoints
    print("\nAvailable API Endpoints:")
    print("-" * 40)
    endpoints = inspector.get_available_endpoints()
    if endpoints:
        endpoint_table = [[
            e['model'],
            e['name'],
            'Yes' if e['is_transient'] else 'No',
            e['field_count']
        ] for e in endpoints]
        print(tabulate(
            endpoint_table,
            headers=['Model', 'Name', 'Transient', 'Field Count'],
            tablefmt='grid'
        ))
    else:
        print("No endpoints found or error occurred.")

    # Save detailed information to JSON file
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'odoo_inspection_report_{timestamp}.json'
        detailed_info = {
            'timestamp': datetime.now().isoformat(),
            'server_info': server_info,
            'modules': modules,
            'endpoints': endpoints
        }
        
        with open(filename, 'w') as f:
            json.dump(detailed_info, f, indent=2)
        
        logger.info(f"Detailed information has been saved to '{filename}'")
    except Exception as e:
        logger.error(f"Error saving report: {str(e)}")

if __name__ == "__main__":
    main() 