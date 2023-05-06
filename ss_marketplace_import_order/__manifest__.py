{
    'name': 'Marketplace Import Order',
    'version': '1.0.0',
    'summary': "Import to odoo's sales order from marketplace",
    'description': "You can import from your marketplace platform to odoo as long as your marketplace platform can export the order as excel",
    'author': 'Samuel Senjaya Hirawan',
    'depends': ['base', 'sale_management', 'sale_stock', 'stock', 'mail', 'delivery'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/marketplace.xml',
        'views/sale_order.xml',
        'views/res_config_settings_views.xml',
        'views/marketplace_menu.xml',
        'views/stock_picking_views.xml',
        'views/product.xml',
        'views/shipping_auto_debit.xml',
        'views/account_views.xml',
    ],
    'images': ['static/description/icon.png'],
    'application': True,
    'license': 'LGPL-3',
    'price': '50',
    'currency': 'USD'
}