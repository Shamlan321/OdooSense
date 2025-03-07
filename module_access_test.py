"""
Odoo Module Access Test

This module provides functionality to test access to various Odoo modules
and their features, ensuring proper installation and configuration.


Author: Shamlan Arshad
License: MIT

"""

import xmlrpc.client
from typing import Dict, List, Any
from tabulate import tabulate
import json
from datetime import datetime, timedelta
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

class OdooModuleTester:
    """Class for testing access to various Odoo modules."""

    def __init__(self):
        self.url = url
        self.db = db
        self.username = username
        self.password = password
        self.uid = None
        self.models = None
        self.results = {}
        self.context = {'lang': os.getenv('DEFAULT_LANGUAGE', 'en_US')}

    def connect(self) -> bool:
        """Establish connection with Odoo server"""
        try:
            common = xmlrpc.client.ServerProxy(common_url)
            self.uid = common.authenticate(self.db, self.username, self.password, {})
            if self.uid:
                self.models = xmlrpc.client.ServerProxy(object_url)
                logger.info(f"Successfully connected to Odoo server at {self.url}")
                return True
            logger.error("Authentication failed")
            return False
        except Exception as e:
            logger.error(f"Connection error: {str(e)}")
            return False

    def check_module_installed(self, module_name: str) -> bool:
        """Check if a specific module is installed"""
        try:
            module_domain = [('name', '=', module_name), ('state', '=', 'installed')]
            module_count = self.models.execute_kw(self.db, self.uid, self.password,
                'ir.module.module', 'search_count', [module_domain]
            )
            return bool(module_count)
        except Exception as e:
            logger.error(f"Error checking module {module_name}: {str(e)}")
            return False

    def test_crm_access(self) -> Dict[str, Any]:
        """Test access to CRM module"""
        try:
            if not self.check_module_installed('crm'):
                return {'status': 'error', 'message': 'CRM module is not installed'}

            lead_fields = ['name', 'partner_id', 'email_from', 'phone', 'type', 'stage_id', 'create_date']
            leads = self.models.execute_kw(self.db, self.uid, self.password,
                'crm.lead', 'search_read',
                [[]], {'fields': lead_fields, 'limit': 10}
            )
            return {
                'status': 'success',
                'record_count': len(leads),
                'sample_data': leads[:5] if leads else []
            }
        except Exception as e:
            logger.error(f"Error testing CRM access: {str(e)}")
            return {'status': 'error', 'message': str(e)}

    def test_sales_access(self) -> Dict[str, Any]:
        """Test access to Sales module"""
        try:
            if not self.check_module_installed('sale'):
                return {'status': 'error', 'message': 'Sales module is not installed'}

            so_fields = ['name', 'partner_id', 'amount_total', 'state', 'date_order']
            orders = self.models.execute_kw(self.db, self.uid, self.password,
                'sale.order', 'search_read',
                [[]], {'fields': so_fields, 'limit': 10}
            )
            
            # Get order lines for each order
            for order in orders:
                order_line_fields = [
                    'product_id',
                    'product_uom_qty',
                    'price_unit',
                    'price_subtotal',
                    'tax_id',
                    'name',
                    'order_id'
                ]
                
                order_lines = self.models.execute_kw(self.db, self.uid, self.password,
                    'sale.order.line', 'search_read',
                    [[('order_id', '=', order['id'])]], 
                    {'fields': order_line_fields}
                )
                
                order['order_lines'] = order_lines

            return {
                'status': 'success',
                'record_count': len(orders),
                'sample_data': orders[:5] if orders else []
            }
        except Exception as e:
            logger.error(f"Error testing Sales access: {str(e)}")
            return {'status': 'error', 'message': str(e)}

    def test_inventory_access(self) -> Dict[str, Any]:
        """Test access to Inventory module"""
        try:
            if not self.check_module_installed('stock'):
                return {'status': 'error', 'message': 'Inventory module is not installed'}

            product_fields = ['name', 'qty_available', 'virtual_available', 'incoming_qty', 'outgoing_qty']
            products = self.models.execute_kw(self.db, self.uid, self.password,
                'product.product', 'search_read',
                [[('type', '=', 'product')]], {'fields': product_fields, 'limit': 10}
            )
            return {
                'status': 'success',
                'record_count': len(products),
                'sample_data': products[:5] if products else []
            }
        except Exception as e:
            logger.error(f"Error testing Inventory access: {str(e)}")
            return {'status': 'error', 'message': str(e)}

    def test_manufacturing_access(self) -> Dict[str, Any]:
        """Test access to Manufacturing module"""
        try:
            # Get manufacturing orders
            mo_fields = ['name', 'product_id', 'product_qty', 'state', 'date_planned_start']
            orders = self.models.execute_kw(self.db, self.uid, self.password,
                'mrp.production', 'search_read', [[]], {'fields': mo_fields, 'limit': 5}
            )
            return {
                'status': 'success',
                'record_count': len(orders),
                'sample_data': orders[:2] if orders else []
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def test_purchase_access(self) -> Dict[str, Any]:
        """Test access to Purchase module"""
        try:
            # Get purchase orders
            po_fields = ['name', 'partner_id', 'amount_total', 'state', 'date_order']
            orders = self.models.execute_kw(self.db, self.uid, self.password,
                'purchase.order', 'search_read', [[]], {'fields': po_fields, 'limit': 5}
            )
            return {
                'status': 'success',
                'record_count': len(orders),
                'sample_data': orders[:2] if orders else []
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def test_accounting_access(self) -> Dict[str, Any]:
        """Test access to Accounting module"""
        try:
            # Updated to use type instead of move_type for invoice type filtering
            invoice_fields = ['name', 'partner_id', 'amount_total', 'state', 'date']
            invoices = self.models.execute_kw(self.db, self.uid, self.password,
                'account.move', 'search_read',
                [[('type', '=', 'out_invoice')]], {'fields': invoice_fields, 'limit': 5}
            )
            return {
                'status': 'success',
                'record_count': len(invoices),
                'sample_data': invoices[:2] if invoices else []
            }
        except Exception as e:
            # If the first attempt fails, try without filtering invoice type
            try:
                invoice_fields = ['name', 'partner_id', 'amount_total', 'state', 'date']
                invoices = self.models.execute_kw(self.db, self.uid, self.password,
                    'account.move', 'search_read',
                    [[]], {'fields': invoice_fields, 'limit': 5}
                )
                return {
                    'status': 'success',
                    'record_count': len(invoices),
                    'sample_data': invoices[:2] if invoices else []
                }
            except Exception as e2:
                return {'status': 'error', 'message': f"First attempt: {str(e)}\nSecond attempt: {str(e2)}"}

    def test_website_access(self) -> Dict[str, Any]:
        """Test access to Website module"""
        try:
            # Get website pages
            page_fields = ['name', 'url', 'website_published', 'create_date']
            pages = self.models.execute_kw(self.db, self.uid, self.password,
                'website.page', 'search_read', [[]], {'fields': page_fields, 'limit': 5}
            )
            return {
                'status': 'success',
                'record_count': len(pages),
                'sample_data': pages[:2] if pages else []
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def run_all_tests(self):
        """Run all module access tests"""
        test_methods = [
            ('CRM', self.test_crm_access),
            ('Sales', self.test_sales_access),
            ('Inventory', self.test_inventory_access),
            ('Manufacturing', self.test_manufacturing_access),
            ('Purchase', self.test_purchase_access),
            ('Accounting', self.test_accounting_access),
            ('Website', self.test_website_access)
        ]

        logger.info("\nStarting Module Access Tests...")
        logger.info(f"Server URL: {self.url}")
        logger.info(f"Database: {self.db}")
        logger.info(f"User ID: {self.uid}")

        for module_name, test_method in test_methods:
            print(f"\nTesting {module_name} module access...")
            result = test_method()
            self.results[module_name] = result
            
            if result['status'] == 'success':
                print(f"✓ Success - Found {result['record_count']} records")
                if result['sample_data']:
                    print("\nSample data:")
                    print(json.dumps(result['sample_data'], indent=2))
            else:
                print(f"✗ Error: {result['message']}")

        # Save results to file
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'module_access_report_{timestamp}.json'
            with open(filename, 'w') as f:
                json.dump({
                    'timestamp': datetime.now().isoformat(),
                    'server_info': {
                        'url': self.url,
                        'database': self.db,
                        'user_id': self.uid
                    },
                    'test_results': self.results
                }, f, indent=2)
            logger.info(f"\nDetailed results have been saved to '{filename}'")
        except Exception as e:
            logger.error(f"Error saving results: {str(e)}")

def main():
    """Main function to run the module access tests."""
    tester = OdooModuleTester()
    
    logger.info("Connecting to Odoo server...")
    if not tester.connect():
        logger.error("Failed to connect to Odoo server.")
        return

    tester.run_all_tests()

if __name__ == "__main__":
    main() 