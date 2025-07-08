from odoo import models, fields, api, exceptions, _
from odoo.tools import float_compare

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
            
class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.model_create_multi
    def create(self, vals_list):
        # Agrupar por order_id para verificar límite por orden
        order_lines_map = {}
        for vals in vals_list:
            order_id = vals.get('order_id')
            if order_id:
                order_lines_map.setdefault(order_id, 0)
                order_lines_map[order_id] += 1

        for order_id, new_lines in order_lines_map.items():
            order = self.env['sale.order'].browse(order_id)
            if len(order.order_line) + new_lines > 30:
                raise exceptions.ValidationError(
                    _('No se pueden agregar más de 30 líneas de producto por orden.')
                )

        # Continuar con lógica original
        for vals in vals_list:
            if vals.get('display_type') or self.default_get(['display_type']).get('display_type'):
                vals['product_uom_qty'] = 0.0

        lines = super().create(vals_list)

        for line in lines:
            if line.product_id and line.state == 'sale':
                msg = _("Extra line with %s", line.product_id.display_name)
                line.order_id.message_post(body=msg)
                if line.product_id.expense_policy not in [False, 'no'] and not line.order_id.analytic_account_id:
                    line.order_id._create_analytic_account()
        return lines

    def write(self, values):
        # Si se cambia de orden, verificar límite
        if 'order_id' in values:
            new_order = self.env['sale.order'].browse(values['order_id'])
            if len(new_order.order_line) + len(self) > 30:
                raise exceptions.ValidationError(
                    _('No se pueden agregar más de 30 líneas de producto por orden.')
                )

        if 'display_type' in values and self.filtered(lambda l: l.display_type != values.get('display_type')):
            raise exceptions.UserError(_("You cannot change the type of a sale order line. Instead you should delete the current line and create a new line of the proper type."))

        if 'product_uom_qty' in values:
            precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
            self.filtered(
                lambda r: r.state == 'sale' and float_compare(r.product_uom_qty, values['product_uom_qty'], precision_digits=precision) != 0)._update_line_quantity(values)

        protected_fields = self._get_protected_fields()
        if 'done' in self.mapped('state') and any(f in values.keys() for f in protected_fields):
            protected_fields_modified = list(set(protected_fields) & set(values.keys()))
            if 'name' in protected_fields_modified and all(self.mapped('is_downpayment')):
                protected_fields_modified.remove('name')

            fields = self.env['ir.model.fields'].sudo().search([
                ('name', 'in', protected_fields_modified), ('model', '=', self._name)
            ])
            if fields:
                raise exceptions.UserError(
                    _('It is forbidden to modify the following fields in a locked order:\n%s')
                    % '\n'.join(fields.mapped('field_description'))
                )

        result = super().write(values)

        if 'product_uom_qty' in values and 'product_packaging_qty' in values and 'product_packaging_id' not in values:
            self.env.remove_to_compute(self._fields['product_packaging_id'], self)

        return result
