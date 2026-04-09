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
    def _get_warehouse_from_location(self, location):
        # Busca el warehouse donde la ubicación de stock principal coincide
        return self.env['stock.warehouse'].search([
            ('lot_stock_id', '=', location.id)
        ], limit=1)

    #partner_id se llena automáticamente con company_id.partner_id

    @api.onchange('picking_type_id')
    def _onchange_picking_type_set_partner(self):
        if self.picking_type_id and self.picking_type_id.code == 'internal':
            self.partner_id = self.company_id.partner_id.id

            # ... (Todo tu código anterior de SaleOrder y SaleOrderLine sigue igual) ...

    # --- NUEVO CÓDIGO PARA COPIAR GLOSA A ALBARÁN ---

    @api.model
    def create(self, vals):
        # 1. Verificamos si el albarán se está creando desde un grupo de abastecimiento
        # (Esto sucede cuando se crea automáticamente desde una Venta)
        if vals.get('group_id'):
            # 2. Buscamos la orden de venta asociada a ese grupo
            # Hacemos un browse seguro para evitar errores si no existe
            group = self.env['procurement.group'].browse(vals['group_id'])
            if group.exists() and group.sale_id:
                # 3. Si existe la venta y tiene glosa, la inyectamos en los valores de creación
                if group.sale_id.glosa:
                    vals['glosa'] = group.sale_id.glosa
        
        # 4. Procedemos con la creación estándar del albarán (con los valores modificados)
        return super().create(vals)