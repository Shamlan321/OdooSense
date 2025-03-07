# Odoo Sense

An intelligent AI-powered assistant that integrates with Odoo ERP to provide natural language interactions for querying and managing various Odoo modules. This project combines the power of Google's Gemini AI with Odoo's comprehensive ERP capabilities.

## 🌟 Features

- 🤖 Natural language processing for Odoo ERP queries
- 📊 Comprehensive module support:
  - CRM and Sales Management
  - Inventory Control
  - Manufacturing Operations
  - Purchase Management
  - Accounting and Invoicing
  - Website and E-commerce
- 💬 Conversational interface with context awareness
- 🔄 Real-time data synchronization
- 📈 Detailed error reporting and debugging
- 🛡️ Secure authentication handling

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- Odoo ERP server (v14.0 or higher)
- Google Cloud account for Gemini AI API

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/odoo-ai-assistant.git
cd odoo-ai-assistant
```

2. Install required packages:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the project root:
```env
ODOO_URL=http://your-odoo-server:8069
ODOO_DB=your_database_name
ODOO_USERNAME=your_username
ODOO_PASSWORD=your_password
GEMINI_API_KEY=your_gemini_api_key
```

### Usage

1. Start the assistant:
```bash
python odoo_llm_integration.py
```

2. Example queries:
```
> Show me all manufacturing orders
> What's the current inventory status?
> List pending sales orders
> Show purchase orders from last week
```

## 🔧 Module Configuration

The assistant supports various Odoo modules. Here's how to configure them:

### Core Modules
- **CRM**: Enable lead and opportunity tracking
- **Sales**: Manage sales orders and quotations
- **Inventory**: Track stock levels and movements
- **Manufacturing**: Monitor production orders
- **Purchase**: Handle purchase orders and vendors
- **Accounting**: Manage invoices and payments

### Additional Tools
- **Module Inspector**: Test module accessibility
- **Cloud Tester**: Verify cloud deployment
- **Local Tester**: Check local installation

## 🔍 Query Keywords

The assistant recognizes different keywords for each module:

| Module | Keywords |
|--------|----------|
| Manufacturing | manufacturing, production, mo, manufacture |
| Sales | sales, sale, so, customer |
| Purchase | purchase, po, supplier, vendor |
| Inventory | inventory, stock, product |
| CRM | lead, opportunity, pipeline |
| Accounting | invoice, bill, payment |

## 🛠️ Development

### Project Structure
```
odoo-ai-assistant/
├── odoo_llm_integration.py    # Main integration file
├── odoo_inspector.py          # Module inspection tool
├── module_access_test.py      # Access testing utility
├── requirements.txt           # Python dependencies
├── .env                       # Environment configuration
└── README.md                 # Documentation
```

### Adding New Features

1. Create a new feature branch:
```bash
git checkout -b feature/your-feature-name
```

2. Implement your changes
3. Add tests if applicable
4. Submit a pull request

## 📝 Error Handling

The assistant includes comprehensive error handling:

- Connection issues
- Authentication failures
- Module access errors
- API rate limits
- Data validation

## 🔐 Security

- Environment variables for sensitive data
- SSL/TLS encryption for connections
- API key management
- Session handling
- Access control

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Odoo Community
- Google Cloud Platform
- Contributors and maintainers

## 📞 Support

For support, please:
1. Check existing issues
2. Create a new issue with detailed information
3. Join our community discussions

---

Made with ❤️ by Shamlan Arshad
