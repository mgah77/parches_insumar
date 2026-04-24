from odoo import models, fields, api, exceptions, _
from odoo.tools import float_compare

import logging
from dateutil.relativedelta import relativedelta

from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class SaleOrderCompany(models.Model):
    _inherit = 'sale.order'  # Reemplaza 'your.model' por el nombre del modelo que deseas modificar

    # Modifica el campo partner_id para agregar un filtro adicional
    partner_id = fields.Many2one(domain="[('type', '!=', 'private'), ('company_id', 'in', (False, company_id)), ('is_company', '=', True), ('type','=','contact')]")
    glosa = fields.Char(string="Glosa", size=40, index=True)

    def _prepare_invoice(self):
        invoice_vals = super()._prepare_invoice()  # Mantén los valores originales
        invoice_vals['glosa'] = self.glosa  # Copia el campo 'glosa' de la venta a la factura
        return invoice_vals
   
    @api.constrains('glosa')
    def _check_glosa_length(self):
        for record in self:
            if record.glosa and len(record.glosa) > 40:
                raise exceptions.ValidationError("La glosa no puede exceder los 40 caracteres")
            
    @api.constrains('order_line')
    def _check_order_line_limit(self):
        for order in self:
            if len(order.order_line) > 30:
                raise exceptions.ValidationError("No se pueden tener más de 30 líneas de producto por orden.")

    
    force_invoiced = fields.Boolean(
        string="Forzar facturado",
        help="Si está activo, la orden se considera totalmente facturada.",
        copy=False,
        tracking=True,  # deja rastro en el chatter con el usuario que hizo el cambio
        readonly=True,
    )

    show_cambiar_estado_facturado_btn = fields.Boolean(
        compute="_compute_show_cambiar_estado_facturado_btn",
        store=False,
    )

    
    @api.depends("date_order")
    def _compute_show_cambiar_estado_facturado_btn(self):
        for order in self:
            if not order.date_order:
                order.show_cambiar_estado_facturado_btn = False
                continue

            today = fields.Date.context_today(order)
            limit_date = today - relativedelta(months=5)

            # date_order es datetime; lo pasamos a fecha en TZ del usuario
            order_date = fields.Datetime.context_timestamp(order, order.date_order).date()
            order.show_cambiar_estado_facturado_btn = order_date <= limit_date

    @api.depends("state", "order_line.invoice_status", "force_invoiced")
    def _compute_invoice_status(self):
        # computo estándar de Odoo
        super()._compute_invoice_status()

        # forzado a "invoiced"
        for order in self.filtered(lambda o: o.force_invoiced and o.state in ("sale", "done")):
            order.invoice_status = "invoiced"

    def action_cambiar_estado_a_facturado(self):
        for order in self:
            if not order.show_cambiar_estado_facturado_btn:
                raise UserError(
                    _("Este botón sólo está disponible si la fecha de la venta es de hace más de 5 meses.")
                )

            if order.invoice_status != "to invoice":
                raise UserError(
                    _("Sólo puedes usar esta acción cuando el estado de facturación está en 'To Invoice'.")
                )

            # marca forzado
            order.write({"force_invoiced": True})

            # Log en chatter (además del tracking del write)
            order.message_post(
                body=_("Cambió el estado de facturación a <b>Facturado</b>. Usuario: %s")
                     % (self.env.user.display_name,),
                subtype_xmlid="mail.mt_note",
            )

        return True


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
            if order.exists():
                existing_lines = len(order.order_line)
            else:
                existing_lines = 0

            total_lines = existing_lines + new_lines
            if total_lines > 30:
                if existing_lines == 0:
                    raise exceptions.ValidationError(
                        _('Estás intentando crear una orden con %s líneas.\n'
                        'El límite es de 30 líneas por orden.') % (new_lines)
                    )
                else:
                    raise exceptions.ValidationError(
                        _('La orden ya tiene %s líneas y estás intentando agregar %s más.\n'
                        'El límite es de 30 líneas por orden.') % (existing_lines, new_lines)
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
            if new_order.exists():
                existing_lines = len(new_order.order_line)
            else:
                existing_lines = 0

            total_lines = existing_lines + len(self)
            if total_lines > 30:
                if existing_lines == 0:
                    raise exceptions.ValidationError(
                        _('Estás intentando mover %s líneas a una orden nueva.\n'
                        'El límite es de 30 líneas por orden.') % len(self)
                    )
                else:
                    raise exceptions.ValidationError(
                        _('La orden ya tiene %s líneas y estás intentando mover %s más.\n'
                        'El límite es de 30 líneas por orden.') % (existing_lines, len(self))
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


    line_number = fields.Integer(string='N° Línea', compute='_compute_line_number', store=False)

    @api.depends('order_id.order_line')
    def _compute_line_number(self):
        for order in self.mapped('order_id'):
            for idx, line in enumerate(order.order_line, start=1):
                line.line_number = idx