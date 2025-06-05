from odoo import models, fields, api

class ProductDepartment(models.Model):
    _inherit = 'product.template'  # Reemplaza 'your.model' por el nombre del modelo que deseas modificar


    exchange_ok = fields.Boolean(string='Para Reemplazo', default=False)

    margenes = fields.Float(string='Margen', compute='_compute_margenes')

    @api.depends('standard_price', 'list_price')
    def _compute_margenes(self):
        for product in self:
            if product.standard_price > 0 and product.list_price > 0:
                # Fórmula: ((Precio venta - Precio costo) / Precio costo) * 100
                product.margenes = ((product.list_price - product.standard_price) / product.standard_price)
            else:
                product.margenes = 0.0