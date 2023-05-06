from odoo import fields, models

class ProductTemplateInherit(models.Model):
    _inherit = 'product.template'

    is_need_converted = fields.Boolean('Is need convert qty from marketplace order?')
    qty_converted = fields.Float('Qty to convert')

class ProductProductInherit(models.Model):
    _inherit = 'product.product'

    is_need_converted = fields.Boolean('Is need convert qty from marketplace order?',related='product_tmpl_id.is_need_converted')
    qty_converted = fields.Float('Qty to convert',related='product_tmpl_id.qty_converted')