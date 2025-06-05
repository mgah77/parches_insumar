from odoo import models, fields

class ProductDepartment(models.Model):
    _inherit = 'product.template'  # Reemplaza 'your.model' por el nombre del modelo que deseas modificar


    exchange_ok = fields.Boolean(string='Para Reemplazo', default=False)

    margenes = fields.Float(string='Margen', store=True, compute='_compute_margen')

    @api.depends('standard_price', 'list_price')
    def _compute_margen(self):
        for product in self:
            if product.standard_price > 0 and product.list_price > 0:
                # Fórmula: ((Precio venta - Precio costo) / Precio costo) * 100
                product.margenes = ((product.list_price - product.standard_price) / product.standard_price) * 100
            else:
                product.margenes = 0.0