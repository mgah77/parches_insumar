from odoo import models, fields, api

class SaleOrderCompany(models.Model):
    _inherit = 'sale.order'  # Reemplaza 'your.model' por el nombre del modelo que deseas modificar

    # Modifica el campo partner_id para agregar un filtro adicional
    partner_id = fields.Many2one(domain="[('type', '!=', 'private'), ('company_id', 'in', (False, company_id)), ('is_company', '=', True), ('type','=','contact')]")
    glosa = fields.Char(string="Glosa", size=40)

    def _prepare_invoice(self):
        invoice_vals = super(SaleOrder, self)._prepare_invoice()  # Mantén los valores originales
        invoice_vals['glosa'] = self.glosa  # Copia el campo 'glosa' de la venta a la factura
        return invoice_vals
   
    @api.constrains('glosa')
    def _check_glosa_length(self):
        for record in self:
            if record.glosa and len(record.glosa) > 40:
                raise ValidationError("La glosa no puede exceder los 40 caracteres")