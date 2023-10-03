from odoo import api, fields, models, _

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    use_marketplace_default_warehouse = fields.Boolean(string="Use Marketplace Default Warehouse")
    marketplace_default_warehouse = fields.Many2one('stock.warehouse', 'Default Warehouse')
    income_account_tokopedia = fields.Many2one(
        'account.account', string='Income Account Tokopedia',
        domain=[('user_type_id', '=', 13)], )  # account income
    income_account_shopee = fields.Many2one(
        'account.account', string='Income Account Shopee',
        domain=[('user_type_id', '=', 13)], )  # account income
    income_account_bukalapak = fields.Many2one(
        'account.account', string='Income Account Bukalapak',
        domain=[('user_type_id', '=', 13)], )  # account income

    def set_values(self):
        res = super(ResConfigSettings, self).set_values()

        self.env['ir.config_parameter'].set_param('marketplace_order_import.use_marketplace_default_warehouse', self.use_marketplace_default_warehouse)
        self.env['ir.config_parameter'].set_param('marketplace_order_import.marketplace_default_warehouse_id', self.marketplace_default_warehouse.id)

        # marketplace account
        self.env['ir.config_parameter'].set_param('marketplace_order_import.income_account_tokopedia_id',
                                                  self.income_account_tokopedia.id)
        self.env['ir.config_parameter'].set_param('marketplace_order_import.income_account_shopee_id',
                                                  self.income_account_shopee.id)
        self.env['ir.config_parameter'].set_param('marketplace_order_import.income_account_bukalapak_id',
                                                  self.income_account_bukalapak.id)

        return res

    def get_values(self):
       """employee limit getting field values"""
       res = super(ResConfigSettings, self).get_values()

       use_marketplace_default_warehouse = self.env['ir.config_parameter'].sudo().get_param('marketplace_order_import.use_marketplace_default_warehouse')
       marketplace_default_warehouse_id = self.env['ir.config_parameter'].sudo().get_param('marketplace_order_import.marketplace_default_warehouse_id')

       income_account_tokopedia_id = self.env['ir.config_parameter'].sudo().get_param(
           'marketplace_order_import.income_account_tokopedia_id')
       income_account_shopee_id = self.env['ir.config_parameter'].sudo().get_param(
           'marketplace_order_import.income_account_shopee_id')
       income_account_bukalapak_id = self.env['ir.config_parameter'].sudo().get_param(
           'marketplace_order_import.income_account_bukalapak_id')


       res.update(
           use_marketplace_default_warehouse = use_marketplace_default_warehouse,
           marketplace_default_warehouse = int(marketplace_default_warehouse_id),
           income_account_tokopedia = int(income_account_tokopedia_id),
           income_account_shopee = int(income_account_shopee_id),
           income_account_bukalapak = int(income_account_bukalapak_id)
       )
       
       return res