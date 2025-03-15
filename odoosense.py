"""
Odoo AI Assistant - Main Integration Module

This module provides an AI-powered interface to interact with Odoo ERP using natural language.
It combines Google's Gemini AI with Odoo's XML-RPC API to provide intelligent responses to queries.

Author: Shamlan Arshad
License: MIT
"""

import xmlrpc.client
from google import genai
import json
from typing import List, Dict, Any
from langchain.tools import Tool
import os
from dotenv import load_dotenv
import logging
from datetime import datetime

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
gemini_api_key = os.getenv('GEMINI_API_KEY', '')

# Connection URLs
common_url = f'{url}/xmlrpc/2/common'
object_url = f'{url}/xmlrpc/2/object'

class ConversationHistory:
    """Manages conversation history and context for the AI assistant."""
    
    def __init__(self):
        self.messages = []
        self.current_context = {}
    
    def add_message(self, role: str, content: str, data: Any = None) -> None:
        """Add a message to the conversation history."""
        message = {
            'role': role,
            'content': content,
            'data': data,
            'timestamp': datetime.now().isoformat()
        }
        self.messages.append(message)
    
    def get_recent_context(self, num_messages: int = 5) -> List[Dict]:
        """Get the most recent messages from the conversation history."""
        return self.messages[-num_messages:] if len(self.messages) > 0 else []
    
    def set_context(self, key: str, value: Any) -> None:
        """Set a context value for the current conversation."""
        self.current_context[key] = value
    
    def get_context(self, key: str) -> Any:
        """Get a context value from the current conversation."""
        return self.current_context.get(key)
    
    def clear_context(self) -> None:
        """Clear the current conversation context."""
        self.current_context = {}

class OdooERPConnector:
    """Handles connection and interactions with the Odoo ERP system."""
    
    def __init__(self):
        self.url = url
        self.db = db
        self.username = username
        self.password = password
        self.uid = None
        self.models = None
        self.results = {}
        self.context = {'lang': 'en_US'}
        self.connect()

    def connect(self) -> bool:
        """Establish connection with Odoo server."""
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

    def check_module(self, module_name):
        if not self.uid:
            return False
        
        module_ids = self.models.execute_kw(self.db, self.uid, self.password,
            'ir.module.module',
            'search_read',
            [[['name', '=', module_name], ['state', '=', 'installed']]],
            {'fields': ['name', 'state']}
        )
        return bool(module_ids)

    def get_manufacturing_orders(self):
        if not self.check_module('mrp'):
            return "Manufacturing module is not installed."
            
        mo_fields = [
            'name',
            'product_id',
            'product_qty',
            'state',
            'date_deadline',
            'date_start',
            'date_finished',
            'production_capacity',
            'components_availability_state'
        ]
        mo_domain = []
        
        orders = self.models.execute_kw(self.db, self.uid, self.password,
            'mrp.production', 'search_read', 
            [mo_domain], 
            {'fields': mo_fields, 'context': self.context}
        )
        
        return [self._format_order(order) for order in orders]

    def get_sales_orders(self):
        if not self.check_module('sale'):
            return "Sales module is not installed."
            
        so_fields = ['name', 'partner_id', 'amount_total', 'state', 'date_order', 'commitment_date']
        so_domain = []
        
        orders = self.models.execute_kw(self.db, self.uid, self.password,
            'sale.order', 'search_read', [so_domain], {'fields': so_fields}
        )
        
        return [self._format_sale_order(order) for order in orders]

    def get_purchase_orders(self):
        if not self.check_module('purchase'):
            return "Purchase module is not installed."
            
        po_fields = ['name', 'partner_id', 'amount_total', 'state', 'date_order', 'date_planned']
        po_domain = []
        
        orders = self.models.execute_kw(self.db, self.uid, self.password,
            'purchase.order', 'search_read', [po_domain], {'fields': po_fields}
        )
        
        return [self._format_purchase_order(order) for order in orders]

    def get_inventory_status(self):
        if not self.check_module('stock'):
            return "Inventory module is not installed."
            
        product_fields = ['name', 'qty_available', 'virtual_available', 'incoming_qty', 'outgoing_qty']
        product_domain = [('type', '=', 'product')]
        
        products = self.models.execute_kw(self.db, self.uid, self.password,
            'product.product', 'search_read', [product_domain], {'fields': product_fields}
        )
        
        return [self._format_product(product) for product in products]

    def get_invoices(self, invoice_type='out_invoice') -> List[Dict]:
        """Get all invoices of specified type"""
        if not self.check_module('account'):
            return "Account module is not installed."
            
        invoice_fields = [
            'name', 'partner_id', 'amount_total', 'state', 
            'invoice_date', 'payment_state', 'currency_id', 'move_type'
        ]
        
        # Use account.move model with move_type field
        domain = [
            ('move_type', '=', invoice_type),
            ('state', '!=', 'draft')
        ]
        
        try:
            invoices = self.models.execute_kw(self.db, self.uid, self.password,
                'account.move',
                'search_read',
                [domain],
                {'fields': invoice_fields}
            )
            
            return [self._format_invoice(invoice) for invoice in invoices]
        except Exception as e:
            print(f"Error fetching invoices: {str(e)}")
            return []

    def get_customer_invoices(self) -> List[Dict]:
        """Get all customer invoices"""
        return self.get_invoices(invoice_type='out_invoice')

    def get_vendor_bills(self) -> List[Dict]:
        """Get all vendor bills"""
        return self.get_invoices(invoice_type='in_invoice')

    def create_customer_invoice(self, partner_id: int, invoice_lines: List[Dict]) -> Dict:
        """Create a new customer invoice"""
        if not self.check_module('account'):
            return "Account module is not installed."
            
        vals = {
            'partner_id': partner_id,
            'move_type': 'out_invoice',
            'invoice_line_ids': [(0, 0, line) for line in invoice_lines]
        }
        
        invoice_id = self.models.execute_kw(self.db, self.uid, self.password,
            'account.move', 'create', [vals]
        )
        return {'status': 'success', 'invoice_id': invoice_id}

    def _format_order(self, order):
        return {
            'reference': order['name'],
            'product': order['product_id'][1] if order['product_id'] else 'N/A',
            'quantity': order['product_qty'],
            'state': order['state'],
            'deadline': order.get('date_deadline', 'Not set'),
            'start_date': order.get('date_start', 'Not set'),
            'end_date': order.get('date_finished', 'Not set'),
            'capacity': order.get('production_capacity', 0),
            'components_status': order.get('components_availability_state', 'unknown')
        }

    def _format_sale_order(self, order):
        return {
            'reference': order['name'],
            'customer': order['partner_id'][1] if order['partner_id'] else 'N/A',
            'amount': order['amount_total'],
            'state': order['state'],
            'order_date': order['date_order'],
            'commitment_date': order['commitment_date'] or 'Not set'
        }

    def _format_purchase_order(self, order):
        return {
            'reference': order['name'],
            'supplier': order['partner_id'][1] if order['partner_id'] else 'N/A',
            'amount': order['amount_total'],
            'state': order['state'],
            'order_date': order['date_order'],
            'scheduled_date': order['date_planned'] or 'Not set'
        }

    def _format_product(self, product):
        return {
            'name': product['name'],
            'on_hand': product['qty_available'],
            'forecasted': product['virtual_available'],
            'incoming': product['incoming_qty'],
            'outgoing': product['outgoing_qty']
        }

    def _format_invoice(self, invoice: Dict) -> Dict:
        """Format invoice data for better readability"""
        return {
            'reference': invoice.get('name', 'N/A'),
            'partner': invoice['partner_id'][1] if invoice.get('partner_id') else 'N/A',
            'amount': invoice.get('amount_total', 0.0),
            'state': invoice.get('state', 'unknown'),
            'date': invoice.get('invoice_date', 'N/A'),
            'payment_status': invoice.get('payment_state', 'unknown'),
            'currency': invoice['currency_id'][1] if invoice.get('currency_id') else 'N/A'
        }

    # Core Business Modules
    def test_crm_access(self) -> Dict[str, Any]:
        """Get CRM leads and opportunities"""
        try:
            lead_fields = ['name', 'partner_id', 'email_from', 'phone', 'type', 'stage_id', 'create_date']
            leads = self.models.execute_kw(self.db, self.uid, self.password,
                'crm.lead', 'search_read', 
                [[]], 
                {'fields': lead_fields, 'limit': 10, 'context': self.context}
            )
            return {
                'status': 'success',
                'record_count': len(leads),
                'data': leads
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def test_sales_access(self) -> Dict[str, Any]:
        """Get sales orders with detailed line items"""
        try:
            so_fields = ['name', 'partner_id', 'amount_total', 'state', 'date_order']
            orders = self.models.execute_kw(self.db, self.uid, self.password,
                'sale.order', 'search_read',
                [[]], 
                {'fields': so_fields, 'limit': 10, 'context': self.context}
            )
            
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
                    {'fields': order_line_fields, 'context': self.context}
                )
                order['order_lines'] = order_lines

            return {
                'status': 'success',
                'record_count': len(orders),
                'data': orders
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def test_inventory_access(self) -> Dict[str, Any]:
        """Get inventory status for products"""
        try:
            product_fields = ['name', 'qty_available', 'virtual_available', 'incoming_qty', 'outgoing_qty']
            products = self.models.execute_kw(self.db, self.uid, self.password,
                'product.product', 'search_read',
                [[('type', '=', 'product')]], 
                {'fields': product_fields, 'context': self.context}
            )
            
            return {
                'status': 'success',
                'record_count': len(products),
                'data': products,
                'error_details': None
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e),
                'error_type': type(e).__name__,
                'full_error': repr(e),
                'traceback': __import__('traceback').format_exc()
            }

    def test_stock_moves_access(self) -> Dict[str, Any]:
        """Get stock movement information"""
        try:
            fields = ['name', 'product_id', 'product_uom_qty', 'location_id', 'location_dest_id', 'state']
            moves = self.models.execute_kw(self.db, self.uid, self.password,
                'stock.move', 'search_read', 
                [[]], 
                {'fields': fields, 'limit': 10, 'context': self.context}
            )
            return {
                'status': 'success',
                'record_count': len(moves),
                'data': moves
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def test_manufacturing_access(self) -> Dict[str, Any]:
        """Get manufacturing orders information"""
        try:
            mo_fields = [
                'name',
                'product_id',
                'product_qty',
                'state',
                'date_deadline',
                'date_start',
                'date_finished',
                'production_capacity',
                'components_availability_state'
            ]
            orders = self.models.execute_kw(self.db, self.uid, self.password,
                'mrp.production', 'search_read', 
                [[]], 
                {'fields': mo_fields, 'limit': 10, 'context': self.context}
            )
            return {
                'status': 'success',
                'record_count': len(orders),
                'data': orders
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def test_website_access(self) -> Dict[str, Any]:
        """Get website pages information"""
        try:
            page_fields = ['name', 'url', 'website_published', 'create_date']
            pages = self.models.execute_kw(self.db, self.uid, self.password,
                'website.page', 'search_read', 
                [[]], 
                {'fields': page_fields, 'limit': 10, 'context': self.context}
            )
            return {
                'status': 'success',
                'record_count': len(pages),
                'data': pages
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def test_ecommerce_products_access(self) -> Dict[str, Any]:
        """Get published eCommerce products"""
        try:
            fields = ['name', 'list_price', 'website_published', 'website_url', 'website_sequence']
            products = self.models.execute_kw(self.db, self.uid, self.password,
                'product.template', 'search_read',
                [[('website_published', '=', True)]], 
                {'fields': fields, 'limit': 10, 'context': self.context}
            )
            return {
                'status': 'success',
                'record_count': len(products),
                'data': products
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def test_invoice_access(self) -> Dict[str, Any]:
        """Get customer invoices information"""
        try:
            invoice_fields = [
                'name', 
                'partner_id', 
                'amount_total', 
                'state', 
                'invoice_date', 
                'payment_state', 
                'currency_id',
                'move_type'
            ]
            domain = [
                ('move_type', '=', 'out_invoice'),
                ('state', '!=', 'draft')
            ]
            
            invoices = self.models.execute_kw(self.db, self.uid, self.password,
                'account.move', 'search_read',
                [domain],
                {'fields': invoice_fields, 'limit': 10, 'context': self.context}
            )
            return {
                'status': 'success',
                'record_count': len(invoices),
                'data': invoices
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def test_vendor_bill_access(self) -> Dict[str, Any]:
        """Get vendor bills information"""
        try:
            bill_fields = [
                'name', 
                'partner_id', 
                'amount_total', 
                'state', 
                'invoice_date', 
                'payment_state', 
                'currency_id',
                'move_type'
            ]
            domain = [
                ('move_type', '=', 'in_invoice'),
                ('state', '!=', 'draft')
            ]
            
            bills = self.models.execute_kw(self.db, self.uid, self.password,
                'account.move', 'search_read',
                [domain],
                {'fields': bill_fields, 'limit': 10, 'context': self.context}
            )
            return {
                'status': 'success',
                'record_count': len(bills),
                'data': bills
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def test_purchase_access(self) -> Dict[str, Any]:
        """Get purchase orders with detailed line items"""
        try:
            po_fields = ['name', 'partner_id', 'amount_total', 'state', 'date_order', 'date_planned']
            orders = self.models.execute_kw(self.db, self.uid, self.password,
                'purchase.order', 'search_read',
                [[]], 
                {'fields': po_fields, 'limit': 10, 'context': self.context}
            )
            
            for order in orders:
                order_line_fields = [
                    'product_id',
                    'product_qty',
                    'price_unit',
                    'price_subtotal',
                    'taxes_id',
                    'name',
                    'order_id'
                ]
                
                order_lines = self.models.execute_kw(self.db, self.uid, self.password,
                    'purchase.order.line', 'search_read',
                    [[('order_id', '=', order['id'])]], 
                    {'fields': order_line_fields, 'context': self.context}
                )
                order['order_lines'] = order_lines

            return {
                'status': 'success',
                'record_count': len(orders),
                'data': orders
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def test_employee_access(self) -> Dict[str, Any]:
        """Get employee information"""
        try:
            employee_fields = [
                'name',
                'job_title',
                'department_id',
                'work_email',
                'work_phone',
                'mobile_phone',
                'parent_id',  # Manager
                'company_id',
                'resource_calendar_id',  # Working hours
                'employee_type',  # Employee type (employee, student, contractor, etc.)
            ]
            
            employees = self.models.execute_kw(self.db, self.uid, self.password,
                'hr.employee', 'search_read',
                [[]], 
                {'fields': employee_fields, 'context': self.context}
            )
            
            return {
                'status': 'success',
                'record_count': len(employees),
                'data': employees
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def install_module(self, module_name: str) -> Dict[str, Any]:
        """Install a module in Odoo"""
        try:
            # First check if module exists
            module_ids = self.models.execute_kw(self.db, self.uid, self.password,
                'ir.module.module',
                'search',
                [[['name', '=', module_name]]]
            )
            
            if not module_ids:
                return {
                    'status': 'error',
                    'message': f'Module {module_name} not found'
                }
            
            # Get module state
            module_data = self.models.execute_kw(self.db, self.uid, self.password,
                'ir.module.module',
                'read',
                [module_ids],
                {'fields': ['state']}
            )
            
            if module_data[0]['state'] == 'installed':
                return {
                    'status': 'success',
                    'message': f'Module {module_name} is already installed'
                }
            
            # Install the module
            self.models.execute_kw(self.db, self.uid, self.password,
                'ir.module.module',
                'button_immediate_install',
                [module_ids]
            )
            
            return {
                'status': 'success',
                'message': f'Module {module_name} has been installed successfully'
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Error installing module: {str(e)}'
            }

    def install_inventory_module(self) -> Dict[str, Any]:
        """Install inventory (stock) module and its dependencies"""
        modules_to_install = ['stock', 'product']
        results = {}
        
        for module in modules_to_install:
            result = self.install_module(module)
            results[module] = result
            
            if result['status'] == 'error':
                return {
                    'status': 'error',
                    'message': f'Failed to install {module}: {result["message"]}'
                }
        
        return {
            'status': 'success',
            'message': 'Inventory module and dependencies installed successfully',
            'details': results
        }

    def create_sample_inventory(self) -> Dict[str, Any]:
        """Create sample inventory records if none exist"""
        try:
            # First create sample products
            sample_products = [
                {'name': 'Sample Product 1', 'type': 'product', 'standard_price': 100},
                {'name': 'Sample Product 2', 'type': 'product', 'standard_price': 200},
                {'name': 'Sample Product 3', 'type': 'product', 'standard_price': 150}
            ]
            
            product_ids = []
            for product in sample_products:
                product_id = self.models.execute_kw(self.db, self.uid, self.password,
                    'product.product', 'create', [product]
                )
                product_ids.append(product_id)
            
            # Create stock inventory adjustments
            for product_id in product_ids:
                inventory_vals = {
                    'name': f'Initial Stock for Product {product_id}',
                    'product_ids': [(4, product_id)],
                    'exhausted': True,
                }
                
                inventory_id = self.models.execute_kw(self.db, self.uid, self.password,
                    'stock.inventory', 'create', [inventory_vals]
                )
                
                # Add inventory line
                line_vals = {
                    'inventory_id': inventory_id,
                    'product_id': product_id,
                    'product_qty': 100,  # Initial quantity
                    'location_id': 8,    # Stock location
                }
                
                self.models.execute_kw(self.db, self.uid, self.password,
                    'stock.inventory.line', 'create', [line_vals]
                )
                
                # Validate inventory
                self.models.execute_kw(self.db, self.uid, self.password,
                    'stock.inventory', 'action_validate',
                    [[inventory_id]]
                )
            
            return {
                'status': 'success',
                'message': 'Sample inventory records created successfully',
                'product_ids': product_ids
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Error creating sample inventory: {str(e)}',
                'error_type': type(e).__name__,
                'full_error': repr(e)
            }

def create_odoo_tools(odoo: OdooERPConnector) -> List[Tool]:
    """Create enhanced tools list with detailed descriptions"""
    tools = [
        Tool(
            name="get_crm_data",
            func=lambda x: json.dumps(odoo.test_crm_access(), indent=2),
            description="Get CRM leads and opportunities. Returns lead details including contact information, status, and creation date."
        ),
        Tool(
            name="get_sales_data",
            func=lambda x: json.dumps(odoo.test_sales_access(), indent=2),
            description="Get sales orders with detailed line items. Returns order information including customer details, products, quantities, and amounts."
        ),
        Tool(
            name="get_inventory_data",
            func=lambda x: json.dumps(odoo.test_inventory_access(), indent=2),
            description="Get inventory status for products. Returns current stock levels, forecasted quantity, incoming and outgoing quantities."
        ),
        Tool(
            name="get_stock_moves",
            func=lambda x: json.dumps(odoo.test_stock_moves_access(), indent=2),
            description="Get stock movement information. Returns details about product movements between locations."
        ),
        Tool(
            name="get_manufacturing_data",
            func=lambda x: json.dumps(odoo.test_manufacturing_access(), indent=2),
            description="Get manufacturing orders information. Returns production orders with product details, quantities, and status."
        ),
        Tool(
            name="get_website_data",
            func=lambda x: json.dumps(odoo.test_website_access(), indent=2),
            description="Get website pages information. Returns published pages, URLs, and creation dates."
        ),
        Tool(
            name="get_ecommerce_data",
            func=lambda x: json.dumps(odoo.test_ecommerce_products_access(), indent=2),
            description="Get published eCommerce products. Returns product details including prices and website information."
        ),
        Tool(
            name="get_customer_invoices",
            func=lambda x: json.dumps(odoo.test_invoice_access(), indent=2),
            description="Get customer invoices information. Returns invoice details including amounts, status, and payment state."
        ),
        Tool(
            name="get_vendor_bills",
            func=lambda x: json.dumps(odoo.test_vendor_bill_access(), indent=2),
            description="Get vendor bills information. Returns bill details including amounts, status, and payment state."
        ),
        Tool(
            name="get_purchase_data",
            func=lambda x: json.dumps(odoo.test_purchase_access(), indent=2),
            description="Get purchase orders with detailed line items. Returns order information including supplier details, products, quantities, and amounts."
        ),
        Tool(
            name="get_employee_data",
            func=lambda x: json.dumps(odoo.test_employee_access(), indent=2),
            description="Get employee information including names, job titles, departments, and contact details."
        )
    ]
    return tools

def get_data_for_query(odoo: OdooERPConnector, query: str) -> Dict:
    """Enhanced query analyzer for better tool selection"""
    # Check if query is conversational
    conversational_keywords = ['hello', 'hi', 'hey', 'how are you', 'good morning', 'good afternoon', 'good evening', 'thanks', 'thank you']
    query_lower = query.lower()
    
    # Return None for conversational queries
    if any(keyword in query_lower for keyword in conversational_keywords):
        return None
    
    # Module installation queries
    if 'install' in query_lower:
        if any(word in query_lower for word in ['inventory', 'stock']):
            return odoo.install_inventory_module()
        # Add more module installation handlers here as needed
        return {'status': 'error', 'message': 'Please specify which module to install'}
    
    # Employee related queries
    if any(word in query_lower for word in ['employee', 'staff', 'worker', 'personnel', 'hr', 'human resource']):
        return odoo.test_employee_access()
    
    # Manufacturing related queries
    if any(word in query_lower for word in ['manufacturing', 'production', 'mo', 'manufacture']):
        return odoo.test_manufacturing_access()
    
    # Sales related queries
    elif any(word in query_lower for word in ['sales', 'sale order', 'customer order', 'quotation']):
        return odoo.test_sales_access()
    
    # Purchase related queries
    elif any(word in query_lower for word in ['purchase', 'po', 'purchase order', 'supplier order', 'vendor order']):
        return odoo.test_purchase_access()
    
    # CRM related queries
    elif any(word in query_lower for word in ['crm', 'lead', 'opportunity', 'pipeline']):
        return odoo.test_crm_access()
    
    # Inventory related queries
    elif any(word in query_lower for word in ['inventory', 'stock level', 'product quantity', 'on hand']):
        return odoo.test_inventory_access()
    
    # Stock movement queries
    elif any(word in query_lower for word in ['stock move', 'movement', 'transfer', 'location']):
        return odoo.test_stock_moves_access()
    
    # Website related queries
    elif any(word in query_lower for word in ['website', 'page', 'web content', 'web page']):
        return odoo.test_website_access()
    
    # eCommerce related queries
    elif any(word in query_lower for word in ['ecommerce', 'online product', 'web shop', 'online store']):
        return odoo.test_ecommerce_products_access()
    
    # Invoice related queries
    elif any(word in query_lower for word in ['invoice', 'customer invoice', 'customer payment', 'customer bill']):
        return odoo.test_invoice_access()
    
    # Vendor bill related queries
    elif any(word in query_lower for word in ['vendor bill', 'supplier invoice', 'supplier payment', 'purchase invoice']):
        return odoo.test_vendor_bill_access()
    
    # Default to CRM if no specific module is mentioned
    else:
        return odoo.test_crm_access()

def process_with_llm(data_response: Dict, user_query: str, conversation_history: ConversationHistory) -> None:
    """
    Process user queries using the Gemini AI model and handle responses.
    
    Args:
        data_response: The data retrieved from Odoo
        user_query: The user's original query
        conversation_history: The conversation history object
    """
    try:
        # Initialize Gemini client with API key from environment
        client = genai.Client(api_key=gemini_api_key)
        
        if not gemini_api_key:
            logger.error("Gemini API key not found in environment variables")
            print("Error: Gemini API key not configured")
            return

        # Get recent conversation context
        recent_messages = conversation_history.get_recent_context()
        conversation_context = "\n".join([
            f"{msg['role']}: {msg['content']}" 
            for msg in recent_messages
        ])

        # Process response based on query type
        if data_response is None:
            prompt = create_conversational_prompt(user_query, conversation_context)
        else:
            prompt = create_data_query_prompt(data_response, user_query, conversation_context)

        # Get response from Gemini
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )

        # Add the interaction to conversation history
        conversation_history.add_message('user', user_query, data_response)
        conversation_history.add_message('assistant', response.text)

        print("\nResponse:")
        print("-" * 40)
        print(response.text)
        print("\n")

    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        print(f"An error occurred while processing your query: {str(e)}")

def create_conversational_prompt(user_query: str, conversation_context: str) -> str:
    """Create a prompt for conversational queries."""
    return f"""You are a helpful AI assistant that can handle both general conversation and Odoo ERP data queries.
This appears to be a conversational query.

Previous Context:
{conversation_context}

Query: {user_query}

Rules for conversational responses:
1. Be friendly and professional
2. Keep responses concise
3. Stay on topic
4. Be helpful
5. If the user asks about capabilities, mention you can help with both general questions and Odoo ERP data"""

def create_data_query_prompt(data_response: Dict, user_query: str, conversation_context: str) -> str:
    """Create a prompt for data-related queries."""
    data_status = format_data_status(data_response)
    
    return f"""You are a helpful AI assistant that can handle both general conversation and Odoo ERP data queries.
This appears to be a data query.

Data Status: {data_status}
Data: {json.dumps(data_response.get('data', []), indent=2) if data_response.get('data') else 'None'}
Query: {user_query}

Rules for data responses:
1. If there's an error, show the complete error message and details for debugging
2. For successful queries, only state what the data shows
3. Use simple, direct language
4. No suggestions or follow-ups
5. For numbers, be exact
6. If no records found, suggest checking the Odoo web interface"""

def format_data_status(data_response: Dict) -> str:
    """Format the data status message based on the response."""
    if data_response["status"] == "error":
        error_details = f"""
Error Message: {data_response.get('message', 'Unknown error')}
Error Type: {data_response.get('error_type', 'N/A')}
Full Error: {data_response.get('full_error', 'N/A')}
Traceback: {data_response.get('traceback', 'N/A')}
"""
        return f"Error occurred: {error_details}"
    elif not data_response.get("data"):
        return "No records found in the system. Please check if records exist in the Odoo web interface."
    else:
        return f"Found {data_response['record_count']} records"

def main():
    """Main function to run the Odoo AI Assistant."""
    odoo = OdooERPConnector()
    if not odoo.uid:
        logger.error("Failed to connect to Odoo server.")
        return

    # Initialize conversation history
    conversation = ConversationHistory()

    print("\nWelcome to Odoo AI Assistant!")
    print("You can ask about:")
    print("- Manufacturing Orders (production, mo)")
    print("- Sales Orders (sales, so)")
    print("- Purchase Orders (purchase, po)")
    print("- Inventory Status (stock, inventory)")
    print("- Customer Invoices (invoice, payment)")
    print("- Vendor Bills (bill, supplier invoice)")
    
    while True:
        try:
            print("\nEnter your query (or 'quit' to exit):")
            user_query = input("> ").strip()
            
            if user_query.lower() in ['quit', 'exit', 'q']:
                print("Goodbye!")
                break
            
            if user_query:
                data_response = get_data_for_query(odoo, user_query)
                process_with_llm(data_response, user_query, conversation)
            else:
                print("Please enter a valid query.")
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            logger.error(f"Error in main loop: {str(e)}")
            print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main() 
