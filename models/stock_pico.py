from odoo import api, fields, models

class stock_picking_kanban(models.Model):
    _name = "stock.pico"
    _description = "DTE"

    name = fields.Char(required=True, readonly=True, default="Venta")
    code = fields.Selection([('incoming', 'Receipt'), ('outgoing', 'Delivery'), ('internal', 'Internal Transfer')], 'Type of Operation', required=True)
    count_picking_draft = fields.Integer(default=1)
    count_picking_ready = fields.Integer(default=2)
    count_picking_waiting = fields.Integer('Current User', default=lambda self: self.env.uid, (domain="[('active', '=', 'True')]))
    count_picking_late = fields.Integer(default=4)
    count_picking_backorders = fields.Integer(default=5)
    color = fields.Integer(default=1)
    warehouse_id = fields.Integer(default=1)
