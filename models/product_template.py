from odoo import models, fields

class ProductDepartment(models.Model):
    _inherit = 'product.template'  # Reemplaza 'your.model' por el nombre del modelo que deseas modificar


    exchange_ok = fields.Boolean(string='Para Reemplazo', default=False)

    margen = fields.Float(
        string='Margen de utilidad (%)',
        compute='_compute_margen',
        store=True,
        digits=(16, 2)  # 2 decimales
    )

    @api.depends('standard_price', 'list_price')
    def _compute_margen(self):
        for product in self:
            if product.standard_price > 0 and product.list_price > 0:
                # Fórmula: ((Precio venta - Precio costo) / Precio costo) * 100
                product.margen = ((product.list_price - product.standard_price) / product.standard_price) * 100
            else:
                product.margen = 0.0

