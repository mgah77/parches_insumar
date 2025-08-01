from odoo import models, fields, api ,_
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
    
    @api.depends('move_type', 'line_ids.amount_residual')
    #hay que filtrar para proveedores aun
    def _compute_payments_widget_reconciled_info(self):
        for move in self:
            payments_widget_vals = {'title': _('Less Payment'), 'outstanding': False, 'content': []}

            if move.state == 'posted' and move.is_invoice(include_receipts=True):
                reconciled_vals = []
                reconciled_partials = move._get_all_reconciled_invoice_partials()
                for reconciled_partial in reconciled_partials:
                    counterpart_line = reconciled_partial['aml']
                    if counterpart_line.move_id.ref:
                        reconciliation_ref = '%s (%s)' % (counterpart_line.move_id.name, counterpart_line.move_id.ref)
                    else:
                        reconciliation_ref = counterpart_line.move_id.name
                    if counterpart_line.amount_currency and counterpart_line.currency_id != counterpart_line.company_id.currency_id:
                        foreign_currency = counterpart_line.currency_id
                    else:
                        foreign_currency = False

                    reconciled_vals.append({
                        'name': counterpart_line.name,
                        'journal_name': counterpart_line.journal_id.name,
                        'amount': abs(counterpart_line.balance),
                        'currency_id': move.company_id.currency_id.id if reconciled_partial['is_exchange'] else reconciled_partial['currency'].id,
                        'date': counterpart_line.date,
                        'partial_id': reconciled_partial['partial_id'],
                        'account_payment_id': counterpart_line.payment_id.id,
                        'payment_method_name': counterpart_line.payment_id.payment_method_line_id.name,
                        'move_id': counterpart_line.move_id.id,
                        'ref': reconciliation_ref,
                        # these are necessary for the views to change depending on the values
                        'is_exchange': reconciled_partial['is_exchange'],
                        'amount_company_currency': formatLang(self.env, abs(counterpart_line.balance), currency_obj=counterpart_line.company_id.currency_id),
                        'amount_foreign_currency': foreign_currency and formatLang(self.env, abs(counterpart_line.amount_currency), currency_obj=foreign_currency)
                    })
                payments_widget_vals['content'] = reconciled_vals

            if payments_widget_vals['content']:
                move.invoice_payments_widget = payments_widget_vals
            else:
                move.invoice_payments_widget = False

    @api.depends(
        'line_ids.matched_debit_ids.debit_move_id.move_id.payment_id.is_matched',
        'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual',
        'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual_currency',
        'line_ids.matched_credit_ids.credit_move_id.move_id.payment_id.is_matched',
        'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual',
        'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual_currency',
        'line_ids.balance',
        'line_ids.currency_id',
        'line_ids.amount_currency',
        'line_ids.amount_residual',
        'line_ids.amount_residual_currency',
        'line_ids.payment_id.state',
        'line_ids.full_reconcile_id',
        'state')
    def _compute_amount(self):
        for move in self:
            if move.move_type in ('in_invoice', 'in_refund'):
                continue

            total_untaxed, total_untaxed_currency = 0.0, 0.0
            total_tax, total_tax_currency = 0.0, 0.0
            total_residual, total_residual_currency = 0.0, 0.0
            total, total_currency = 0.0, 0.0

            for line in move.line_ids:
                if move.is_invoice(True):
                    # === Invoices ===
                    if line.display_type == 'tax' or (line.display_type == 'rounding' and line.tax_repartition_line_id):
                        # Tax amount.
                        total_tax += line.balance
                        total_tax_currency += line.amount_currency
                        total += line.balance
                        total_currency += line.amount_currency
                    elif line.display_type in ('product', 'rounding'):
                        # Untaxed amount.
                        total_untaxed += line.balance
                        total_untaxed_currency += line.amount_currency
                        total += line.balance
                        total_currency += line.amount_currency
                    elif line.display_type == 'payment_term':
                        # Residual amount.
                        total_residual += line.amount_residual
                        total_residual_currency += line.amount_residual_currency
                else:
                    # === Miscellaneous journal entry ===
                    if line.debit:
                        total += line.balance
                        total_currency += line.amount_currency

            sign = move.direction_sign
            move.amount_untaxed = sign * total_untaxed_currency
            move.amount_tax = sign * total_tax_currency
            move.amount_total = sign * total_currency
            move.amount_residual = -sign * total_residual_currency
            move.amount_untaxed_signed = -total_untaxed
            move.amount_tax_signed = -total_tax
            move.amount_total_signed = abs(total) if move.move_type == 'entry' else -total
            move.amount_residual_signed = total_residual
            move.amount_total_in_currency_signed = abs(move.amount_total) if move.move_type == 'entry' else -(sign * move.amount_total)    

    @api.depends('amount_residual', 'move_type', 'state', 'company_id')
    def _compute_payment_state(self):
        stored_ids = tuple(self.ids)
        if stored_ids:
            self.env['account.partial.reconcile'].flush_model()
            self.env['account.payment'].flush_model(['is_matched'])

            queries = []
            for source_field, counterpart_field in (('debit', 'credit'), ('credit', 'debit')):
                queries.append(f'''
                    SELECT
                        source_line.id AS source_line_id,
                        source_line.move_id AS source_move_id,
                        account.account_type AS source_line_account_type,
                        ARRAY_AGG(counterpart_move.move_type) AS counterpart_move_types,
                        COALESCE(BOOL_AND(COALESCE(pay.is_matched, FALSE))
                            FILTER (WHERE counterpart_move.payment_id IS NOT NULL), TRUE) AS all_payments_matched,
                        BOOL_OR(COALESCE(BOOL(pay.id), FALSE)) as has_payment,
                        BOOL_OR(COALESCE(BOOL(counterpart_move.statement_line_id), FALSE)) as has_st_line
                    FROM account_partial_reconcile part
                    JOIN account_move_line source_line ON source_line.id = part.{source_field}_move_id
                    JOIN account_account account ON account.id = source_line.account_id
                    JOIN account_move_line counterpart_line ON counterpart_line.id = part.{counterpart_field}_move_id
                    JOIN account_move counterpart_move ON counterpart_move.id = counterpart_line.move_id
                    LEFT JOIN account_payment pay ON pay.id = counterpart_move.payment_id
                    WHERE source_line.move_id IN %s AND counterpart_line.move_id != source_line.move_id
                    GROUP BY source_line_id, source_move_id, source_line_account_type
                ''')

            self._cr.execute(' UNION ALL '.join(queries), [stored_ids, stored_ids])

            payment_data = defaultdict(lambda: [])
            for row in self._cr.dictfetchall():
                payment_data[row['source_move_id']].append(row)
        else:
            payment_data = {}

        for invoice in self:
            if invoice.payment_state == 'invoicing_legacy':
                # invoicing_legacy state is set via SQL when setting setting field
                # invoicing_switch_threshold (defined in account_accountant).
                # The only way of going out of this state is through this setting,
                # so we don't recompute it here.
                continue

            currencies = invoice._get_lines_onchange_currency().currency_id
            currency = currencies if len(currencies) == 1 else invoice.company_id.currency_id
            reconciliation_vals = payment_data.get(invoice.id, [])
            payment_state_matters = invoice.is_invoice(True)

            # Restrict on 'receivable'/'payable' lines for invoices/expense entries.
            if payment_state_matters:
                reconciliation_vals = [x for x in reconciliation_vals if x['source_line_account_type'] in ('asset_receivable', 'liability_payable')]

            new_pmt_state = 'not_paid'
            if invoice.state == 'posted':

                # Posted invoice/expense entry.
                if payment_state_matters:

                    if currency.is_zero(invoice.amount_residual):
                        if any(x['has_payment'] or x['has_st_line'] for x in reconciliation_vals):

                            # Check if the invoice/expense entry is fully paid or 'in_payment'.
                            if all(x['all_payments_matched'] for x in reconciliation_vals):
                                new_pmt_state = 'paid'
                            else:
                                new_pmt_state = invoice._get_invoice_in_payment_state()

                        else:
                            new_pmt_state = 'paid'

                            reverse_move_types = set()
                            for x in reconciliation_vals:
                                for move_type in x['counterpart_move_types']:
                                    reverse_move_types.add(move_type)

                            in_reverse = (invoice.move_type in ('in_invoice', 'in_receipt')
                                          and (reverse_move_types == {'in_refund'} or reverse_move_types == {'in_refund', 'entry'}))
                            out_reverse = (invoice.move_type in ('out_invoice', 'out_receipt')
                                           and (reverse_move_types == {'out_refund'} or reverse_move_types == {'out_refund', 'entry'}))
                            misc_reverse = (invoice.move_type in ('entry', 'out_refund', 'in_refund')
                                            and reverse_move_types == {'entry'})
                            if in_reverse or out_reverse or misc_reverse:
                                new_pmt_state = 'reversed'

                    elif reconciliation_vals:
                        new_pmt_state = 'partial'
                        
            if invoice.amount_residual == 0:
                invoice.payment_state = 'paid'
            else:
                invoice.payment_state = new_pmt_state



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

