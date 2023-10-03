from odoo import fields, models

class SaleReport(models.Model):
    _inherit = "sale.report"

    marketplace_order_id = fields.Char('Marketplace Order Id', track_visibility='onchange')

    def _select_pos(self, fields=None):
        res = super()._select_pos(fields)
        res += ',NULL as marketplace_order_id'

        return res
    
    def _select_sale(self, fields=None):
        res = super()._select_sale(fields)
        res += ',s.marketplace_order_id as marketplace_order_id' 

        return res