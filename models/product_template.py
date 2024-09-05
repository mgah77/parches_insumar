from odoo import models, fields

class ProductDepartment(models.Model):
    _inherit = 'product.template'  # Reemplaza 'your.model' por el nombre del modelo que deseas modificar

    # Modifica el campo partner_id para agregar un filtro adicional
    depto = fields.Many2one('taller.depto.rel', string='Depto')
    alias = fields.Char('Detalle')