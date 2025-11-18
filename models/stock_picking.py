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

    warehouse_view_ids = fields.Many2many(
        comodel_name='stock.location',
        compute='_compute_warehouse_views',
        string='Ubicaciones raíz'
    )

    @api.depends()
    def _compute_warehouse_views(self):
        warehouses = self.env['stock.warehouse'].search([])
        ids = warehouses.mapped('view_location_id').ids
        for rec in self:
            rec.warehouse_view_ids = [(6, 0, ids)]

    @api.depends('picking_type_id')
    def _compute_user_stock_location(self):
        for record in self:
            warehouse = self.env.user.property_warehouse_id
            if warehouse:
                record.user_stock_location_id = warehouse.lot_stock_id
            else:
                record.user_stock_location_id = False
    
    
    @api.model
    def _get_recepciones_location(self, warehouse_view_location):
        """Devuelve la sububicación 'Recepciones' bajo la bodega destino."""
        return self.env['stock.location'].search([
            ('location_id', '=', warehouse_view_location.id),
            ('name', '=', 'Recepciones'),
        ], limit=1)

    @api.model
    def _get_recepciones_picking_type(self, warehouse):
        """Devuelve el picking.type de entrada (incoming) llamado 'Recepciones'
           para el warehouse indicado."""
        return self.env['stock.picking.type'].search([
            ('code', '=', 'incoming'),
            ('name', '=', 'Recepciones'),
            ('warehouse_id', '=', warehouse.id),
        ], limit=1)

    def action_confirm(self):
        # Primero confirmamos normalmente
        res = super().action_confirm()

        for picking in self:

            # Solo aplicamos la lógica a transferencias internas
            if picking.picking_type_code != 'internal':
                continue

            destino_usuario = picking.location_dest_id

            # El usuario selecciona una bodega (usage='view', sin padre)
            if destino_usuario.usage == 'view' and not destino_usuario.location_id:

                # 1) Sububicación Recepciones dentro de esa bodega
                recepciones_loc = self._get_recepciones_location(destino_usuario)
                if not recepciones_loc:
                    continue  # si la bodega no tiene Recepciones, no hacemos nada

                # 2) Tipo de operación 'Recepciones' (incoming) para esa bodega
                # Para saber la bodega → tomamos warehouse_id de la ubicación raíz
                warehouse = destino_usuario.get_warehouse()
                if not warehouse:
                    continue

                recepciones_type = self._get_recepciones_picking_type(warehouse)
                if not recepciones_type:
                    continue

                # 3) Reemplazar destino y tipo de picking
                picking.location_dest_id = recepciones_loc
                picking.picking_type_id = recepciones_type

        return res