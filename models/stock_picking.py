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

    def action_confirm(self):
        res = super().action_confirm()

        for picking in self:
            # Solo las transferencias internas
            if picking.picking_type_code != 'internal':
                continue

            # Destino que eligió el usuario: normalmente 'Stock' de la bodega destino
            stock_dest = picking.location_dest_id
            if not stock_dest:
                continue

            # Obtener la bodega a partir de esa ubicación de stock
            warehouse = stock_dest.get_warehouse()
            if not warehouse:
                continue

            # Buscar ubicación 'Recepciones' de esa bodega
            recepciones_loc = self._get_recepciones_location(warehouse)
            if not recepciones_loc:
                continue

            # Buscar picking type incoming 'Recepciones' de esa bodega
            recepciones_type = self._get_recepciones_picking_type(warehouse)
            if not recepciones_type:
                continue

            # Reemplazar destino y tipo de operación
            picking.location_dest_id = recepciones_loc
            picking.picking_type_id = recepciones_type

        return res