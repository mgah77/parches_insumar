from odoo import models, fields, api ,_
from collections import defaultdict
from odoo.tools import (
    date_utils,
    email_re,
    email_split,
    float_compare,
    float_is_zero,
    float_repr,
    format_amount,
    format_date,
    formatLang,
    frozendict,
    get_lang,
    is_html_empty,
    sql
)

class AccountMove(models.Model):
    _inherit = 'account.move'

    glosa = fields.Char(string="Glosa")
    document_number = fields.Char(related='partner_id.document_number', string="RUT", store=False)
    


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    glosa = fields.Char(string="Glosa", index=True)

    @api.depends('product_id')
    def _compute_name(self):
        for line in self:
            if line.display_type == 'payment_term':
                if line.move_id.payment_reference:
                    line.name = line.move_id.payment_reference
                elif not line.name:
                    line.name = ''
                continue
            if not line.product_id or line.display_type in ('line_section', 'line_note'):
                continue
            if line.partner_id.lang:
                product = line.product_id.with_context(lang=line.partner_id.lang)
            else:
                product = line.product_id

            values = []
            # Eliminamos la línea que agrega product.partner_ref (código interno)
            if line.journal_id.type == 'sale':
                if product.description_sale:
                    values.append(product.description_sale)
            elif line.journal_id.type == 'purchase':
                if product.description_purchase:
                    values.append(product.description_purchase)
            # Si no hay descripción específica, usar el nombre del producto
            if not values:
                values.append(product.name)
            line.name = '\n'.join(values)

