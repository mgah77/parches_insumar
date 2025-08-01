from odoo import models, fields, api, _

class AccountPaymentRegisterCustom(models.TransientModel):
    _inherit = 'account.payment.register'

    amount_total = fields.Monetary(currency_field='currency_id', store=True, readonly=False)

    @api.depends('line_ids')
    def _compute_amount(self):
        for wizard in self:
            move = None
            if wizard.env.context.get('active_model') == 'account.move':
                move_ids = wizard.env.context.get('active_ids')
                if move_ids:
                    move = wizard.env['account.move'].browse(move_ids[0])
            elif wizard.line_ids:
                move = wizard.line_ids[0].move_id

            wizard.amount = abs(move.amount_residual) if move else 0.0
            wizard.amount_total = abs(move.amount_total) if move else 0.0 
            wizard.write({'amount_total': move.amount_total})

    
    @api.depends('can_edit_wizard', 'amount')
    def _compute_payment_difference(self):
        for wizard in self:
            move = None
            if wizard.env.context.get('active_model') == 'account.move':
                move_ids = wizard.env.context.get('active_ids')
                if move_ids:
                    move = wizard.env['account.move'].browse(move_ids[0])
            elif wizard.line_ids:
                move = wizard.line_ids[0].move_id

            if move:
                expected = abs(move.amount_residual)
                wizard.payment_difference = expected - wizard.amount
            else:
                wizard.payment_difference = 0.0


        # 🔧 Escritura SQL DESPUÉS de que todo Odoo haya terminado sus cálculos
    def action_create_payments(self):
        payments = self._create_payments()

        # ⏬ Forzar valores al final del proceso

        for wizard in self:
            if wizard.env.context.get('active_model') == 'account.move':
                move_ids = wizard.env.context.get('active_ids', [])                
                pagado = wizard.amount

                for move_id in move_ids:
                    move = wizard.env['account.move'].browse(move_id)
                    total = move.amount_residual
                    nuevo_residual = int(round(total - pagado))
                    estado = 'paid' if nuevo_residual == 0 else 'partial'

                    # Actualizar el encabezado de factura
                    wizard.env.cr.execute("""
                        UPDATE account_move
                        SET amount_residual = %s,
                            payment_state = %s
                        WHERE id = %s
                    """, (nuevo_residual, estado, move_id))

                    # Solo si se paga completamente, marcar líneas como conciliadas
                    # Conciliación manual si el residuo es cero
                    if nuevo_residual == 0:
                        # Obtener líneas de factura reconciliables
                        self.env.cr.execute("""
                            SELECT id, debit, credit, amount_currency, currency_id
                            FROM account_move_line
                            WHERE move_id = %s
                            AND display_type IS payment_term
                            AND account_id IN (
                                SELECT id FROM account_account WHERE reconcile = true
                            )
                        """, (move_id,))
                        lineas_factura = self.env.cr.fetchall()

                        # Obtener líneas de pago reconciliables
                        self.env.cr.execute("""
                            SELECT aml.id, aml.debit, aml.credit, aml.amount_currency, aml.currency_id
                            FROM account_move_line aml
                            JOIN account_move am ON aml.move_id = am.id
                            WHERE am.payment_id = %s
                            AND aml.account_id IN (
                                SELECT id FROM account_account WHERE reconcile = true
                            )
                        """, (payments.id,))
                        lineas_pago = self.env.cr.fetchall()

                        for linea_fact in lineas_factura:
                            for linea_pago in lineas_pago:
                                amount_fact = linea_fact[1] or linea_fact[2]
                                amount_pago = linea_pago[2] or linea_pago[1]
                                amount = min(amount_fact, amount_pago)
                                if amount == 0:
                                    continue

                                debit_id = linea_fact[0] if linea_fact[1] else linea_pago[0]
                                credit_id = linea_pago[0] if linea_fact[1] else linea_fact[0]

                                self.env.cr.execute("""
                                    INSERT INTO account_partial_reconcile (
                                        debit_move_id, credit_move_id,
                                        amount,
                                        debit_amount_currency, credit_amount_currency,
                                        debit_currency_id, credit_currency_id,
                                        create_date, write_date
                                    ) VALUES (
                                        %s, %s,
                                        %s,
                                        %s, %s,
                                        %s, %s,
                                        NOW(), NOW()
                                    )
                                """, (
                                    debit_id,
                                    credit_id,
                                    amount,
                                    linea_fact[3],
                                    linea_pago[3],
                                    linea_fact[4],
                                    linea_pago[4]
                                ))

        if self._context.get('dont_redirect_to_payments'):
            return True

        # Redirección estándar
        action = {
            'name': _('Payments'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'context': {'create': False},
        }
        if len(payments) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': payments.id,
            })
        else:
            action.update({
                'view_mode': 'tree,form',
                'domain': [('id', 'in', payments.ids)],
            })
        return action
