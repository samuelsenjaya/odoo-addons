from odoo import models, fields, api
from odoo.exceptions import ValidationError
from xlrd import open_workbook
import base64
from datetime import datetime

class Platform(models.Model):
    _name = "platform"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Name', track_visibility='onchange')
    code = fields.Char('Code', track_visibility='onchange')
    prefix = fields.Char('Prefix', track_visibility='onchange')
    # warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse', track_visibility='onchange')
    
    order_id = fields.Char('Order Id', track_visibility='onchange')
    status = fields.Char('Status', track_visibility='onchange')
    date_order = fields.Char('Order Date', track_visibility='onchange')
    product_sku = fields.Char('Product Sku', track_visibility='onchange')
    product_name = fields.Char('Product Name', track_visibility='onchange')
    product_qty = fields.Char('Product Qty', track_visibility='onchange')
    product_price = fields.Char('Product Price', track_visibility='onchange')
    shipping_price = fields.Char('Shipping Price', track_visibility='onchange')
    shipping_courier = fields.Char('Shipping Courier', track_visibility='onchange')
    customer_phone = fields.Char('Customer Phone', track_visibility='onchange')
    customer_name = fields.Char('Customer Name', track_visibility='onchange')
    is_price_per_product = fields.Boolean('Is Price per Product', default=True, track_visibility='onchange')
    date_format = fields.Char('Date Format', track_visibility='onchange')
    has_precision_price = fields.Boolean('Has Precision for Price?', track_visibility='onchange')
    precision_symbol = fields.Char('Precision Symbol', track_visibility='onchange')
    is_shipping_price_per_product = fields.Boolean('Is Shippping Price per Product', default=False, track_visibility='onchange')
    income_account = fields.Many2one('account.account', string='Income Account', domain=[('user_type_id', '=', 13)], track_visibility='onchange')
    tracking_number = fields.Char('Tracking Number', track_visibility='onchange')

    @api.model
    def create(self, vals):
        res = super(Platform, self).create(vals)

        sequence = self.env['ir.sequence'].search([('code', '=', vals['code'])])
        if not sequence:
            self.env['ir.sequence'].create({
                'name': vals['name'] + ' Sequence',
                'code': vals['code'],
                'prefix': vals['prefix'],
                'padding': 5
            })
        # else:
        #     raise ValidationError(u'You have already have the platform with same code')

        return res
    
    def write(self, vals):
        sequence = self.env['ir.sequence'].search([('code', '=', self.code)])

        res = super(Platform, self).write(vals)

    # def name_get(self):
    #     result = []

    #     for rec in self:
    #         result.append((rec.id, '%s - %s'  %(rec.name, rec.warehouse_id.name)))

    #     return result

    def unlink(self):
        sequence = self.env['ir.sequence'].search([('code', '=', self.code)])
        sequence.unlink()

        return super(Platform, self).unlink()

    def import_order(self, order_file, marketplace_id):
        try:
            wb = open_workbook(file_contents = base64.decodebytes((order_file)))
            marketplace_model = self.env['marketplace'].browse([marketplace_id])
            
            for sheet in wb.sheets():
                transaction_data = marketplace_model.convert_data_to_dict(sheet._cell_values)
                order_data = []
                for data in transaction_data:
                    # if not self.env['marketplace'].is_order_cancelled(data[self.status]) :
                    order_data.append(self._mapped_data(data))
                    marketplace_model.create_order(order_data[-1], self)
                
                marketplace_model.confirm_all_imported_order(order_data)
                return True #assuming always use first sheet only
        except TypeError as e:
            raise ValidationError(u'ERROR: {}'.format(e))
        
    def _mapped_data(self, data):
        order_data = {}

        order_data['order_id'] = data[self.order_id] if self.order_id in data.keys() else ''
        order_data['status'] = data[self.status] if self.status in data.keys() else ''
        order_data['date_order'] = datetime.strptime(data[self.date_order], self.date_format) if self.date_order in data.keys() else ''
        order_data['product_sku'] = data[self.product_sku] if self.product_sku in data.keys() else ''
        order_data['product_name'] = data[self.product_name] if self.product_name in data.keys() else ''
        order_data['product_qty'] = data[self.product_qty] if self.product_qty in data.keys() else '1'

        data_product_price = data[self.product_price] if self.product_price in data.keys() else ''
        if self.is_price_per_product:
            order_data['product_price'] = self.env['marketplace'].get_number_from_string(data_product_price, self.has_precision_price, self.precision_symbol)
        else:
            # bukalapak doesn't have product per price
            if order_data['product_qty']:
                product_total_price = data_product_price
                if product_total_price:
                    product_total_price = float(product_total_price)
                    product_qty = float(order_data['product_qty'])
                    product_price = product_total_price / product_qty
                    order_data['product_price'] = str(product_price)

        order_data['shipping_price'] = self.env['marketplace'].get_number_from_string(data[self.shipping_price], self.has_precision_price, self.precision_symbol) if self.shipping_price in data.keys() else ''
        order_data['shipping_courier'] = data[self.shipping_courier] if self.shipping_courier in data.keys() else ''
        order_data['customer_phone'] = data[self.customer_phone] if self.customer_phone in data.keys() else ''
        order_data['customer_name'] = data[self.customer_name] if self.customer_name in data.keys() else ''
        order_data['tracking_number'] = data[self.tracking_number] if self.tracking_number in data.keys() else ''

        return order_data
    
    def _convert_to_datetime(self, date):
        return datetime.strptime(date, '%Y-%m-%d %H:%M:%S %z')
