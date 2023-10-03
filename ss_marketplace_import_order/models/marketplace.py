from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import date, datetime
import pytz
import re

MARKETPLACE = [
    ('tokopedia', 'Tokopedia'),
    ('shopee', 'Shopee'),
    ('bukalapak', 'Bukalapak')
]
MARKETPLACE_DICT = {
    'tokopedia': 'Tokopedia',
    'shopee': 'Shopee',
    'bukalapak': 'Bukalapak'
}

class Marketplace(models.Model):
    _name = 'marketplace'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    STATUS = [
        ('draft', 'Draft'),
        ('imported', 'Imported')
    ]
    MAX_LENGTH_SKU = 9

    def _get_team_member_by_user_id(self, uid):
        return self.env['crm.team.member'].search([('user_id', '=', uid)], limit=1)

    def _default_warehouse(self):
        use_marketplace_default_warehouse = self.env['ir.config_parameter'].sudo().get_param(
            'marketplace_order_import.use_marketplace_default_warehouse')
        marketplace_default_warehouse = self.env['ir.config_parameter'].sudo().get_param(
            'marketplace_order_import.marketplace_default_warehouse_id')
        
        if use_marketplace_default_warehouse and marketplace_default_warehouse:
           return self.env['stock.warehouse'].browse([int(marketplace_default_warehouse)])

        return self.env['stock.warehouse']

    def _default_team_id(self):
        current_user_id = int(self.env.uid)
        default_team = self.env['crm.team']
        if current_user_id:
            current_team_member = self._get_team_member_by_user_id(current_user_id)
            default_team = default_team.browse(int(current_team_member.crm_team_id.id))

        return default_team

    @api.onchange('sale_person_id')
    def _onchange_sale_person_id(self):
        for rec in self:
            sale_person = rec.sale_person_id
            if sale_person.id:
                user_id = sale_person.id
                current_team_member = self._get_team_member_by_user_id(user_id)
                rec.team_id = current_team_member.crm_team_id.id     

    name = fields.Char("Name", required=True, readonly=True, default= lambda self: _('New'))
    order_file = fields.Binary(string="Order File", required=True, track_visibility='onchange')
    order_file_name = fields.Char('Order File Name', track_visibility='onchange')
    platform = fields.Selection(MARKETPLACE, string="Platform", track_visibility='onchange')
    platform_id = fields.Many2one('platform', required=True, string="Platform", track_visibility='onchange')
    state = fields.Selection(STATUS, readonly=True, string="State", default="draft",track_visibility='onchange')
    sale_person_id = fields.Many2one('res.users', string='Salesperson', track_visibility='onchange')
    team_id = fields.Many2one('crm.team', string='Sales Team', track_visibility='onchange')
    source_warehouse = fields.Many2one('stock.warehouse', 'Warehouse', required=True, default=_default_warehouse, track_visibility='onchange')
    delivery_count = fields.Integer(string='Delivery Orders', compute='_compute_picking_count')
    order_count = fields.Integer(string="Orders", compute='_compute_order_count')
    invoice_count = fields.Integer(string="Invoices", compute="_compute_invoice_count")
    starting_row = fields.Integer(string="Starting Row at", default=1, help="Please see the excel, which row is the starting point of the table")
    # order_ids = fields.One2many('sale.order', 'marketplace_import_order_id', 'Order Ids')

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            platform_id = vals.get('platform_id')
            platform = self.env['platform'].browse(platform_id)
            vals['name'] = self.env['ir.sequence'].next_by_code(platform.code) or _('New')

        res = super(Marketplace, self).create(vals)
        return res

    def get_number_from_string(self, string, has_precision, precision_symbol):
        if isinstance(string, float) or isinstance(string, int):
            return string

        if has_precision:
            before, sep, after = string.partition(precision_symbol)
            string = before
        
        number_in_array = re.findall(r'\d+', string)
        if isinstance(number_in_array, list):
            return ''.join(map(str, number_in_array))
    
        return number_in_array
            
    def _compute_order_count(self):
        for marketplace in self:
            orders = marketplace._get_orders()
            marketplace.order_count = len(orders)

    def _compute_picking_count(self):
        for marketplace in self:
            orders = marketplace._get_orders()
            delivery_count = 0

            for order in orders:
                delivery_count += len(order.picking_ids)
            marketplace.delivery_count = delivery_count

    def _compute_invoice_count(self):
        for marketplace in self:
            orders = marketplace._get_orders()
            invoice_count = 0

            for order in orders:
                invoice_count += len(order.invoice_ids)

            marketplace.invoice_count = invoice_count            
            
    def _get_orders(self):
        return self.env['sale.order'].search([('marketplace_import_order_id', '=', self.id)])

    def action_open_sale_order(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("sale.action_orders")
        action['domain'] = [('marketplace_import_order_id', '=', self.id)]

        return action

    def action_open_stock_picking(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("stock.action_picking_tree_all")
        orders = self._get_orders()
        picking_ids = []

        for order in orders:
            pickings = order.mapped('picking_ids').ids
            picking_ids.extend(pickings)

        action['domain'] = [('id', 'in', picking_ids)]
        return action

    def action_open_invoice(self):
        self.ensure_one()
        orders = self._get_orders()
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_out_invoice_type")
        invoice_ids = []

        for order in orders:
            invoices = order.mapped('invoice_ids').ids
            invoice_ids.extend(invoices)
        action['domain'] = [('id', 'in', invoice_ids)]
        return action

    def import_order(self):
        marketplace = self.platform_id
        if marketplace.import_order(self.order_file, self.id) : 
            marketplace_model = self.browse([self.id])
            order_count = len(marketplace_model._get_orders())
            
            if order_count:
                self.state = 'imported'
                # raise ValidationError(u'No Order created for this file, please check it again and make sure the file is include new order in it' )

    
    def convert_data_to_dict(self, data):
        transaction_data = []
        starting_row = self.starting_row
        data_key = starting_row - 1 if starting_row - 1 >= 0 else 0
        for row in range(starting_row,len(data)):
            transaction_dict = {}
            for col in range(len(data[row])):
                key = data[data_key][col]
                transaction_dict[key] = data[row][col]
            transaction_data.append(transaction_dict)
        return transaction_data        
                
    def confirm_all_imported_order(self, order_data):
        marketplace_order_ids = self._get_all_marketplace_order_id(order_data)

        # for marketplace_order_id in list(dict.fromkeys(marketplace_order_ids)):
        for data in order_data:
            if 'order_id' in data:
                marketplace_order_id = data['order_id']
                marketplace_status = data['status']
                sale_order = self.env['sale.order'].search([('marketplace_order_id', '=', marketplace_order_id)])
                date_order = sale_order.date_order
                if not self.is_order_cancelled(marketplace_status):
                    if (len(sale_order) == 1):
                        sale_order.action_confirm()
                        sale_order.date_order = date_order
                        self._create_invoice(sale_order)
                    elif (len(sale_order) > 1):
                        sale_order_ids = ", ".join(sale_order.ids)
                        raise ValidationError(u'Cannot Confirm ORDER! \nDuplicate Marketplace Order ID from Sale Order ID: ' + sale_order_ids )
                    else: raise ValidationError(u"Cannot Confirm ORDER! \nNo Order with Marketplace Order ID: " + marketplace_order_id)
                else:
                    invoices = sale_order.invoice_ids
                    for invoice in invoices:
                        invoice.button_draft()
                        invoice.button_cancel()
            

    def _create_invoice(self, sale_order):
        if sale_order.invoice_status == 'to invoice':
            invoice = sale_order._create_invoices()
            invoice.invoice_date = sale_order.date_order
            invoice.invoice_date_due = sale_order.date_order
            invoice.action_post()

    def _get_all_marketplace_order_id(self, order_data):
        return [data['order_id'] for data in order_data if 'order_id' in data]


    def get_partner(self, data):
        partner_model = self.env['res.partner']
        customer_phone = data['customer_phone']
        customer_name = data['customer_name']

        partner = partner_model.search([('mobile', '=', customer_phone)], limit = 1)

        if (partner.id) :
            return partner
        else :
            new_customer = partner.create({
                'name': customer_name,
                'mobile': customer_phone
            })

            return new_customer

    def _trim_sku(self, data_sku):
        sku = data_sku[:self.MAX_LENGTH_SKU]

        return sku

    def _get_order_by_data_order(self, data):
        return self.env['sale.order'].search([('marketplace_order_id', '=', data['order_id']), ('state', 'not in', ['cancel'])])

    def is_order_cancelled(self, status):
        status = status.lower()
        return status.__contains__('batal') or status.__contains__('dikembalikan')

    def _add_shipping_to_order(self, data, platform):
        order_line = []
        sale_order = self._get_order_by_data_order(data)
        shipping_product = self.env['product.product'].browse(1382) #hardcode get shipping product by id
        shipping_price = data['shipping_price']
        shipping_courier = data['shipping_courier']
        shipping_auto_debit = self.env['shipping.auto.debit'].search([('is_active', '=' , 1), ('platform_id', '=', platform.id), ('name', '=', shipping_courier)])

        if (shipping_product and shipping_price and shipping_price != '0' and not shipping_auto_debit) :
            if not sale_order.id :
                order_line = [
                    (0,0,{
                        'product_id': shipping_product.id,
                        'price_unit': shipping_price,
                        'name': shipping_courier,
                        'product_uom_qty': 1
                    })
                ]
            elif sale_order.id and platform.is_shipping_price_per_product:
                for line in sale_order.order_line:
                    if line.product_id == shipping_product:
                        line.price_unit += float(shipping_price)
    
        return order_line
        
    def create_order(self, data, platform):
        """Handles create order when importing from excel

        :param dicts data: data from excel will be store in dictionary
        :param model platform
        """
        sale_order = self._get_order_by_data_order(data)
        product = self.env['product.template'].search([('default_code', '=', self._trim_sku(data['product_sku']))], limit=1)
        
        #skip if status 'batal' or 'dikembalikan' 
        if not sale_order.id and self.is_order_cancelled(data['status']):
            return
        
        partner = self.get_partner(data)
        date_order = data['date_order']
        if (isinstance(date_order, datetime)):
            current_tz = self.env.context.get('tz') or self.env.user.tz
            timezone = pytz.timezone(current_tz)
            if date_order.tzinfo is None :
                with_timezone = timezone.localize(date_order)
            else: with_timezone = date_order

            date_order = with_timezone.astimezone(pytz.UTC) # convert to GMT
            date_order = date_order.strftime('%Y-%m-%d %H:%M:%S')
        product_id = product.product_variant_id.id
        product_qty = float(data['product_qty'])
        product_price = float(data['product_price'])

        if (product.is_need_converted):
            product_qty *= product.qty_converted
            product_price = round((float(data['product_qty']) * float(data['product_price'])) / product_qty,0)

        if (product_id):
            order_line = self._add_shipping_to_order(data, platform)
            order_line += [
                (0,0,{
                    'product_id': product_id,
                    'price_unit': product_price,
                    'product_uom_qty': product_qty
                })
            ]
            if sale_order.id :
                if self.is_order_cancelled(data['status']):
                    sale_order.with_context({'disable_cancel_warning': True}).action_cancel()
                    sale_order.marketplace_order_status = data['status']
                else :
                    if sale_order.state in ['done', 'sale']:
                        sale_order.marketplace_order_status = data['status']
                    elif sale_order.state == 'draft':
                        product_exists = False
                        for line in sale_order.order_line:
                            if product_id == line.product_id.id:
                                line.product_uom_qty += product_qty
                                product_exists = True

                        if not product_exists:
                            sale_order.write({
                                'order_line': order_line
                            })
            elif not (sale_order) and not self.is_order_cancelled(data['status']) :
                sale_order.create({
                    'partner_id': partner.id,
                    'date_order': date_order,
                    'marketplace_order_id': data['order_id'],
                    # 'marketplace_name': platform,
                    'marketplace_platform': platform.id,
                    'user_id': self.sale_person_id.id,
                    'team_id': self.team_id.id,
                    'order_line': order_line,
                    'marketplace_import_order_id': self.id,
                    'warehouse_id': self.source_warehouse.id,
                    'marketplace_order_status': data['status'],
                    'marketplace_tracking_number': data['tracking_number'],
                    'marketplace_courier': data['shipping_courier']
                })
            # else: 
            #     raise ValidationError(u"This file had been imported! Please make sure the file is correct.")

        else:
            raise ValidationError(u"Cannot Create Order! \nThere is no product on system with SKU: " + data['product_sku'])


class ShippingAutoDebit(models.Model):
    _name = 'shipping.auto.debit'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Shipping Courier', required=True, track_visibility='onchange')
    platform = fields.Selection(MARKETPLACE, string="Platform", track_visibility='onchange')
    platform_id = fields.Many2one('platform', 'Platform', required=True, track_visibility='onchange')
    is_active = fields.Boolean('Enable', track_visibility='onchange')

    def name_get(self):
        result = []

        for rec in self:
            result.append((rec.id, '%s - %s'  %(rec.platform_id.name, rec.name)))

        return result
    
class ResPartner(models.Model):
    _inherit = 'res.partner'

    mobile = fields.Char('Mobile')
    _sql_constraints = [('mobile_uniq', 'unique(mobile)', 'Mobile phone must be different!')]

class SalesOrder(models.Model):
    _inherit = "sale.order"
    
    marketplace_order_id = fields.Char('Marketplace Order Id', track_visibility='onchange')
    marketplace_name = fields.Selection(MARKETPLACE, track_visibility='onchange')
    marketplace_platform = fields.Many2one('platform', 'Platform', track_visibility='onchange')
    marketplace_import_order_id = fields.Many2one('marketplace', 'Marketplace Import Order',  readonly=True,track_visibility='onchange')
    marketplace_order_status = fields.Char('Marketplace Status', readonly=True, track_visibility='onchange')
    marketplace_tracking_number = fields.Char('Marketplace Tracking Number', readonly=True, track_visibility='onchange')
    marketplace_courier = fields.Char('Marketplace Courier', readonly=True, track_visibility='onchange')

class StockPicking(models.Model):
    _inherit = "stock.picking"
    
    marketplace_order_id = fields.Char(related="sale_id.marketplace_order_id", readonly=True, track_visibility='onchange')
    marketplace_name = fields.Selection(related="sale_id.marketplace_name", readonly=True, track_visibility='onchange')
    marketplace_platform = fields.Many2one('platform', 'Platform', related='sale_id.marketplace_platform', readonly=True, track_visibility='onchange')
    marketplace_import_order_id = fields.Many2one(related="sale_id.marketplace_import_order_id", readonly=True, track_visibility='onchange')
    marketplace_order_status = fields.Char(related='sale_id.marketplace_order_status', readonly=True, track_visibility='onchange')
    marketplace_tracking_number = fields.Char(related='sale_id.marketplace_tracking_number', readonly=True, track_visibility='onchange')
    marketplace_courier = fields.Char(related='sale_id.marketplace_courier', readonly=True, track_visibility='onchange')