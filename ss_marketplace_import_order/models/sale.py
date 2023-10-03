from odoo import models, api
from odoo.osv import expression

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def name_get(self):
        res = []
        for order in self:
            name = order.name
            if order.marketplace_order_id:
                name = '%s - %s' %(name, order.marketplace_order_id)
            if self._context.get('sale_show_partner_name') and order.partner_id.name:
                name = '%s - %s' % (name, order.partner_id.name)
            res.append((order.id, name))

        return res
    
    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        if self._context.get('sale_show_partner_name'):
            if operator == 'ilike' and not (name or '').strip():
                domain = []
            elif operator in ('ilike', 'like', '=', '=like', '=ilike'):
                domain = expression.AND([
                    args or [],
                    ['|', ('name', operator, name), ('partner_id.name', operator, name),('marketplace_order_id', operator, name)]
                ])
                return self._search(domain, limit=limit, access_rights_uid=name_get_uid)
        if operator == 'ilike' and not (name or '').strip():
            domain = []
        elif operator in ('ilike', 'like', '=', '=like', '=ilike'):
            domain = expression.AND([
                args or [],
                ['|', ('name', operator, name), ('marketplace_order_id', operator, name)]
            ])
            return self._search(domain, limit=limit, access_rights_uid=name_get_uid)
        return super(SaleOrder, self)._name_search(name, args=args, operator=operator, limit=limit, name_get_uid=name_get_uid)