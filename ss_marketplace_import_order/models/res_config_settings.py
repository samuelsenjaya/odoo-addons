from odoo import api, fields, models, _

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    use_marketplace_default_warehouse = fields.Boolean(string="Use Marketplace Default Warehouse")
    marketplace_default_warehouse = fields.Many2one('stock.warehouse', 'Default Warehouse')

    def set_values(self):
        res = super(ResConfigSettings, self).set_values()

        self.env['ir.config_parameter'].set_param('marketplace_order_import.use_marketplace_default_warehouse', self.use_marketplace_default_warehouse)
        self.env['ir.config_parameter'].set_param('marketplace_order_import.marketplace_default_warehouse_id', self.marketplace_default_warehouse.id)

        return res

    def get_values(self):
       """employee limit getting field values"""
       res = super(ResConfigSettings, self).get_values()

       use_marketplace_default_warehouse = self.env['ir.config_parameter'].sudo().get_param('marketplace_order_import.use_marketplace_default_warehouse')
       marketplace_default_warehouse_id = self.env['ir.config_parameter'].sudo().get_param('marketplace_order_import.marketplace_default_warehouse_id')

       res.update(
           use_marketplace_default_warehouse = use_marketplace_default_warehouse,
           marketplace_default_warehouse = int(marketplace_default_warehouse_id)
       )
       
       return res