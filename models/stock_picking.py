from odoo import api, fields, models

class stock_picking_custom_kanban(models.Model):
    _inherit = 'stock.picking.type'

    user_warehouse = fields.Integer('Current User', compute="_compute_user")

    def _compute_user(self):
        for record in self:
            record['user_warehouse']=self.env.user.property_warehouse_id
            return


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    user_stock_location_id = fields.Many2one(
        'stock.location',
        compute='_compute_user_stock_location',
        store=False
    )


    @api.depends('picking_type_id')
    def _compute_user_stock_location(self):
        for record in self:
            warehouse = self.env.user.property_warehouse_id
            if warehouse:
                record.user_stock_location_id = warehouse.lot_stock_id
            else:
                record.user_stock_location_id = False
    
    

    @api.model
    def _get_recepciones_location(self, warehouse):
        """Sububicación 'Recepciones' de la bodega destino."""
        return self.env['stock.location'].search([
            ('location_id', '=', warehouse.view_location_id.id),
            ('name', '=', 'Recepciones'),
        ], limit=1)

    @api.model
    def _get_recepciones_picking_type(self, warehouse):
        """Tipo de operación incoming 'Recepciones' de esa bodega."""
        return self.env['stock.picking.type'].search([
            ('code', '=', 'incoming'),
            ('name', '=', 'Recepciones'),
            ('warehouse_id', '=', warehouse.id),
        ], limit=1)

    def button_validate(self):
        res = super().button_validate()

        for picking in self:

            # Solo si el tipo original es interno
            if picking.picking_type_id.code != 'internal':
                continue

            destino_actual = picking.location_dest_id
            if not destino_actual:
                continue

            # Obtener bodega desde la ubicación actual de destino (Stock)
            warehouse = self.env['stock.warehouse'].search([
                ('lot_stock_id', '=', destino_actual.id)
            ], limit=1)
            if not warehouse:
                continue

            # Buscar ubicación de Recepciones (hija de view_location_id)
            recepciones_loc = self.env['stock.location'].search([
                ('location_id', '=', warehouse.view_location_id.id),
                ('name', 'ilike', 'recepcion')
            ], limit=1)
            if not recepciones_loc:
                continue

            # Buscar tipo de operación 'Recepciones' (incoming) de esta bodega
            recepciones_type = self.env['stock.picking.type'].search([
                ('code', '=', 'incoming'),
                ('name', 'ilike', 'recepcion'),
                ('warehouse_id', '=', warehouse.id),
            ], limit=1)
            if not recepciones_type:
                continue

            # Sobrescribir destino y tipo de picking DESPUÉS de validar
            picking.location_dest_id = recepciones_loc
            picking.picking_type_id = recepciones_type

        return res