from odoo import api, fields, models, _

class PlatformAccount(models.Model):
    _name = 'platform.account'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    _sql_constraints = [('warehouse_platform_uniq', 'unique(warehouse_id, platform_id)', 'Combination Warehouse & Platform must be different!')]

    name = fields.Char("Name", required=True, readonly=True, default= lambda self: _('New'))
    platform_id = fields.Many2one('platform', string="Platform", required=True, track_visibility='onchange')
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse', required=True, track_visibility='onchange')
    income_account_id = fields.Many2one('account.account', string='Income Account', domain=[('user_type_id', '=', 13)], required=True, track_visibility='onchange')

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            platform_id = vals.get('platform_id')
            warehouse_id = vals.get('warehouse_id')
            
            platform = self.env['platform'].browse(platform_id)
            warehouse = self.env['stock.warehouse'].browse(warehouse_id)

            vals['name'] = platform.name + ' - ' + warehouse.name or _('New')

        res = super(PlatformAccount, self).create(vals)
        return res