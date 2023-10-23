from odoo import models, fields, _
from odoo.exceptions import ValidationError


class SaleOrderCompany(models.Model):
    _inherit = 'sale.order'  # Reemplaza 'your.model' por el nombre del modelo que deseas modificar

    # Modifica el campo partner_id para agregar un filtro adicional
    partner_id = fields.Many2one(domain="[('type', '!=', 'private'), ('company_id', 'in', (False, company_id)), ('is_company', '=', True)]"
