from odoo import api, fields, models

MARKETPLACE_DICT = {
    'tokopedia': 'Tokopedia',
    'shopee': 'Shopee',
    'bukalapak': 'Bukalapak'
}

class AccountMoveLine(models.Model):
    _inherit = 'account.move'

    marketplace_order_id = fields.Char('Marketplace Order Id', compute='_get_marketplace_data',
                                       store=True, readonly=True)
    marketplace_name = fields.Char('Marketplace Name', compute='_get_marketplace_data',
                                   store=True, readonly=True)
    marketplace_order_status = fields.Char('Marketplace Status', compute='_get_marketplace_data',
                                           store=True, readonly=True)

    @api.depends('invoice_line_ids','invoice_line_ids.sale_line_ids.state','invoice_line_ids.sale_line_ids.order_id.marketplace_order_status')
    def _get_marketplace_data(self):
        for account_move in self:
            sale_order_ids = account_move.invoice_line_ids.mapped('sale_line_ids').order_id.filtered(
                lambda r:r.state not in ('draft','sent','cancel'))

            marketplace_order_ids = []
            marketplace_names = []
            marketplace_order_ids_status = []
            if sale_order_ids:
                for so in sale_order_ids:
                    so_name = so.name
                    marketplace_order_id = so.marketplace_order_id
                    marketplace_name = so.marketplace_platform.name
                    marketplace_order_status = so.marketplace_order_status

                    if marketplace_order_id:
                        marketplace_order_ids.append(marketplace_order_id)
                        marketplace_order_ids_status.append(marketplace_order_status)

                    if (marketplace_name not in marketplace_names):
                        marketplace_names.append(marketplace_name)

            account_move.marketplace_order_id = ', '.join(marketplace_order_ids) if any(marketplace_order_ids) else False
            account_move.marketplace_name = ', '.join(marketplace_names) if any(marketplace_names) else False
            account_move.marketplace_order_status = ', '.join(marketplace_order_ids_status) if any(marketplace_order_ids_status) else False

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    marketplace_order_id = fields.Char('Marketplace Order Id', compute='_get_marketplace_data',
                                       store=True, readonly=True)
    marketplace_name = fields.Char('Marketplace Name', compute='_get_marketplace_data',
                                   store=True, readonly=True)
    marketplace_order_status = fields.Char('Marketplace Status', compute='_get_marketplace_data',
                                           store=True, readonly=True)

    def _get_marketplace_data(self):
        for move_line in self:
            sale_order_ids = move_line.mapped('sale_line_ids').order_id.filtered(
                lambda r:r.state not in ('draft','sent','cancel'))
                
            marketplace_order_ids = []
            marketplace_names = []
            marketplace_order_ids_status = []
            if sale_order_ids:
                for so in sale_order_ids:
                    so_name = so.name
                    marketplace_order_id = so.marketplace_order_id
                    marketplace_name = so.marketplace_platform.name
                    marketplace_order_status = so.marketplace_order_status

                    if marketplace_order_id:
                        marketplace_order_ids.append(marketplace_order_id)
                        marketplace_order_ids_status.append(marketplace_order_status)

                    if (marketplace_name not in marketplace_names):
                        marketplace_names.append(marketplace_name)

            move_line.marketplace_order_id = ', '.join(marketplace_order_ids) if marketplace_order_ids else False
            move_line.marketplace_name = ', '.join(marketplace_names) if marketplace_names else False
            move_line.marketplace_order_status = ', '.join(marketplace_order_ids_status) if marketplace_order_ids_status else False
            

    def _get_computed_account(self):
        is_sale_document = self.move_id.is_sale_document(include_receipts=True)
        if is_sale_document and self.sale_line_ids:
            sale_order = self.sale_line_ids.mapped('order_id')
            # for future, need to know how to handle SO more than 1
            if len(sale_order):
                marketplace_platform = sale_order.marketplace_platform
                # marketplace_type = sale_order.marketplace_name
                delivery_xml_id = self.env.ref('delivery.product_category_deliveries').id 
                categ_id = self.product_id.categ_id.id
                
                # for manually create marketplace order
                if marketplace_platform and categ_id != delivery_xml_id:
                    income_account_id = marketplace_platform.income_account.id

                    if income_account_id:
                        account = self.env['account.account'].browse([int(income_account_id)])
                        return account

        res = super(AccountMoveLine,self)._get_computed_account()
        return res
