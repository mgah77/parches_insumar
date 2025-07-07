from odoo import models, fields, api

class SaleOrderCompany(models.Model):
    _inherit = 'sale.order'  # Reemplaza 'your.model' por el nombre del modelo que deseas modificar

    # Modifica el campo partner_id para agregar un filtro adicional
    partner_id = fields.Many2one(domain="[('type', '!=', 'private'), ('company_id', 'in', (False, company_id)), ('is_company', '=', True), ('type','=','contact')]")
    glosa = fields.Char(string="Glosa")

    def _prepare_invoice(self):
        invoice_vals = super(SaleOrder, self)._prepare_invoice()  # Mantén los valores originales
        invoice_vals['glosa'] = self.glosa  # Copia el campo 'glosa' de la venta a la factura
        return invoice_vals