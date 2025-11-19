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
            ('name', 'ilike', 'Recepcion'),
            ('warehouse_id', '=', warehouse.id),
        ], limit=1)

    def button_validate(self):
        for picking in self:

            # Solo queremos transformar las transferencias internas
            if picking.picking_type_id.code != 'internal':
                continue

            # Warehouse asociado al tipo de operación actual
            warehouse = picking.picking_type_id.warehouse_id
            if not warehouse:
                continue

            # Tipo de operación 'Recepciones' (incoming) de ESA bodega
            recepciones_type = self.env['stock.picking.type'].search([
                ('code', '=', 'incoming'),
                ('name', '=', 'Recepciones'),
                ('warehouse_id', '=', warehouse.id),
            ], limit=1)
            if not recepciones_type:
                continue

            # Ubicación destino configurada en el tipo 'Recepciones'
            dest_loc = recepciones_type.default_location_dest_id or warehouse.wh_input_stock_loc_id
            if not dest_loc:
                continue

            # Cambiar tipo de operación y destino ANTES de validar
            picking.picking_type_id = recepciones_type
            picking.location_dest_id = dest_loc

            # Cambiar destino de todos los movimientos
            picking.move_ids_without_package.write({
                'location_dest_id': dest_loc.id,
            })
            picking.move_line_ids.write({
                'location_dest_id': dest_loc.id,
            })

        # Validar ya con el tipo 'Recepciones' y la ubicación destino correcta
        return super().button_validate()