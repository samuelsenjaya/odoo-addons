{
    'name': 'Indonesian Marketplace Data',
    'version': '1.0.0',
    'summary': "Indonesia marketplace like Tokopedia, Bukalapak, Shopee, Lazada",
    'description': "This module will import platform data for Indonesian marketplace (Tokopedia, Bukalapak, Shopee, Lazada)",
    'author': 'Samuel Senjaya Hirawan',
    'depends': ['base', 'ss_marketplace_import_order'],
    'data': [
        'data/platform_data.xml',
    ],
    'images': ['static/description/icon.png'],
    'application': False,
    'license': 'LGPL-3',
}