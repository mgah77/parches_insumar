from odoo import models, fields

class ProductDepartment(models.Model):
    _inherit = 'product.template'  # Reemplaza 'your.model' por el nombre del modelo que deseas modificar


    exchange_ok = fields.Boolean(string='Para Reemplazo', default=False)
    sucursal = fields.Selection([('2','Ñuble'),('3','Par Vial')],string='Sucursal')

