from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class MarketplaceDelivery (models.Model):
    _name = 'marketplace.delivery'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'list of marketplace order for delivery'
    _order = 'create_date desc'

    STATUS = [
        ('draft', 'Draft'),
        ('waiting', 'Waiting'),
        ('ready', 'Ready'),
        ('done', 'Done')
    ]

    name = fields.Char("Name", required=True, readonly=True, default= lambda self: _('New'))
    line_ids = fields.One2many('marketplace.delivery.line', 'marketplace_delivery_id', string='Delivery Line')
    state = fields.Selection(STATUS, readonly=True, string="State", default="draft", compute="_compute_state", track_visibility='onchange')
    marketplace_courier_count = fields.One2many('marketplace.courier.count', 'marketplace_delivery_id', string="Courier Count")
    product_count = fields.Float('Product Count')
    order_count = fields.Float('Order Count')
    courier_per_marketplace = fields.Html('Marketplace')
    
    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('marketplace.delivery') or _('New')
        self.state = 'waiting'
        res = super(MarketplaceDelivery, self).create(vals)
        return res
    
    def action_assign(self):
        if not self.line_ids:
            raise ValidationError(u"Please add Tracking Number or Marketplace Order Id")
        for line in self.line_ids:
            order = line.sale_id
            if order.id:
                picking = self.env['stock.picking'].search([('marketplace_order_id', '=', order.marketplace_order_id), ('state', 'not in', ['done', 'cancel'])])
                if picking and picking.id:
                    picking.action_assign()
    
    def action_validate(self):
        if not self.line_ids:
            raise ValidationError(u"Please add Tracking Number or Marketplace Order Id")
        for line in self.line_ids:
            order = line.sale_id
            if order.id:
                picking = self.env['stock.picking'].search([('marketplace_order_id', '=', order.marketplace_order_id), ('state', 'not in', ['done', 'cancel'])])
                if picking and picking.id:
                    picking.action_set_quantities_to_reservation()
                    picking.button_validate()
    
    def _get_product_count(self, line_ids):
        product_list = {}
        product_count = 0
        for line in line_ids:
            picking = line.picking_id
            if picking and picking.id:
                for move in picking.move_lines:
                    key = move.product_id
                    qty = move.product_uom_qty
                    if key in product_list:
                        product_list[key] += qty
                    else:
                        product_list[key] = qty
                    product_count += qty
        return product_count

    def _get_courier_count(self, line_ids):
        courier_list = {}
        marketplace_courier = self.env['marketplace.courier']

        for line in line_ids:
            if line.marketplace_courier:
                courier = marketplace_courier.get_marketplace_courier(line.marketplace_courier)
                platform = line.sale_id.marketplace_platform
                if courier:
                    key = courier.name + ' - ' + platform.name

                    if key in courier_list:
                        courier_list[key] += 1
                    else :
                        courier_list[key] = 1
        
        vals = []
        for courier_name, count in courier_list.items():
            vals.append([0, 0, {
                'courier_name': courier_name,
                'courier_count': count
            }])

        return vals

    def _get_courier_per_marketplace(self, line_ids):
        marketplace_courier_count = ''
        marketplace_courier_list = {}
        marketplace_order_list = {}

        for line in line_ids:
                
            platform = line.sale_id.marketplace_platform
            if platform:
                key = platform
                if key in marketplace_order_list:
                    marketplace_order_list[key] += 1
                else: marketplace_order_list[key] = 1

                if line.marketplace_courier:
                    if key in marketplace_courier_list:
                        marketplace_courier_list[key] += 1
                    else: marketplace_courier_list[key] = 1


        for marketplace in marketplace_courier_list:
            if marketplace.id:
                marketplace_courier_count += '<b>' + marketplace.name + ' Courier </b>: ' + str(marketplace_courier_list[marketplace]) + '<br />'

        for marketplace in marketplace_order_list:
            if marketplace.id:
                marketplace_courier_count += '<b>' + marketplace.name + ' Order </b>: ' + str(marketplace_order_list[marketplace]) + '<br />'
                
        return marketplace_courier_count

    @api.onchange('line_ids')
    def _onchange_line_ids(self):
        vals = self._get_courier_count(self.line_ids)
        self.marketplace_courier_count = [(6,0,[])]
        self.marketplace_courier_count = vals
        self.product_count = self._get_product_count(self.line_ids)
        self.courier_per_marketplace = self._get_courier_per_marketplace(self.line_ids)
        
        order_count = self.line_ids.filtered(lambda r:r.sale_id.id != False) 
        self.order_count = len(order_count)

    @api.depends('line_ids')
    def _compute_state(self):
        for delivery in self:
            order_count = delivery.line_ids.filtered(lambda r:r.sale_id.id != False) 
            if len(delivery.line_ids) > 0 and len(order_count) > 0:
                picking_state = delivery.line_ids.picking_id.mapped('state')
                products_availability = delivery.line_ids.filtered(lambda r:r.products_availability != False).mapped('products_availability')

                if all(availability.lower() in ['available'] for availability in products_availability) and all(state in ['assigned'] for state in picking_state):
                    delivery.state = 'ready'
                else:
                    delivery.state = 'waiting'

                if all(state in ['done'] for state in picking_state):
                    delivery.state = 'done'
            else:
                delivery.state = 'draft'
                
            
class MarketplaceDeliveryLine (models.Model):
    _name = 'marketplace.delivery.line'
    _sql_constraints = [('marketplace_order_unique', 'unique(sale_id)', 'Marketplace Order Id must be unique')]

    marketplace_delivery_id = fields.Many2one('marketplace.delivery', 'Marketplace Delivery')
    marketplace_tracking_number = fields.Char('Tracking Number')
    sale_id = fields.Many2one('sale.order', 'Sales Order', domain="[('marketplace_order_id', '!=', False), ('state', 'not in',  ['cancel'])]")
    picking_id = fields.Many2one('stock.picking', 'Transfer', domain="[('marketplace_order_id', '!=', False), ('state', 'not in',  ['cancel'])]")
    picking_status = fields.Selection(related='picking_id.state', store=True)
    products_availability = fields.Char(related='picking_id.products_availability', store=True)
    products_availability_state = fields.Selection(related='picking_id.products_availability_state', store=True)
    marketplace_courier = fields.Char(related='sale_id.marketplace_courier', readonly=True, track_visibility='onchange')
    
    @api.onchange('sale_id')
    def _onchange_sale_id(self):
        for rec in self:
            order = rec.sale_id
            if order.id:
                marketplace_order_id = order.marketplace_order_id
                picking = rec.env['stock.picking'].search([('marketplace_order_id', '=', marketplace_order_id)])

                if picking.id:
                    rec.picking_id = picking
                    
                if order.marketplace_tracking_number:
                    rec.marketplace_tracking_number = order.marketplace_tracking_number

    @api.onchange('marketplace_tracking_number')
    def _onchange_marketplace_tracking_number(self):
        for rec in self:
            if rec.marketplace_tracking_number:
                order = rec.env['sale.order'].search([('marketplace_tracking_number', '=', rec.marketplace_tracking_number), ('state', 'not in',  ['cancel'])])
                picking = rec.env['stock.picking'].search([('marketplace_tracking_number', '=', rec.marketplace_tracking_number),('state', 'not in',  ['cancel'])])

                if order.id:
                    rec.sale_id = order

                if picking.id:
                    rec.picking_id = picking

class MarketplaceCourierCount(models.Model):
    _name = 'marketplace.courier.count'

    # marketplace_courier_id = fields.Many2one('marketplace.courier', 'Marketplace Courier')
    courier_name = fields.Char('Courier Name')
    courier_count = fields.Float('Count')
    marketplace_delivery_id = fields.Many2one('marketplace.delivery', 'Marketplace Delivery')

class MarketplaceCourier(models.Model):
    _name = 'marketplace.courier'

    name = fields.Char('Courier Name')

    def get_marketplace_courier(Self, courier_name):
        marketplace_courier = Self.search([])
        courier_name = courier_name.lower().replace(" ", "")

        for courier in marketplace_courier:
            if courier_name.__contains__(courier.name.lower().replace(" ", "")):
                return courier
        
        return False
