from odoo import models, api, _

class AccountPaymentRegisterCustom(models.TransientModel):
    _inherit = 'account.payment.register'

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

            # Usar amount_residual solo como valor por defecto, editable por el usuario
            wizard.amount = abs(move.amount_residual) if move else 0.0
    
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


    def _create_payments(self):
        self.ensure_one()
        batches = self._get_batches()
        first_batch_result = batches[0]
        edit_mode = self.can_edit_wizard and (len(first_batch_result['lines']) == 1 or self.group_payment)
        to_process = []

        if edit_mode:
            payment_vals = self._create_payment_vals_from_wizard(first_batch_result)
            to_process.append({
                'create_vals': payment_vals,
                'to_reconcile': first_batch_result['lines'],
                'batch': first_batch_result,
            })
        else:
            if not self.group_payment:
                new_batches = []
                for batch_result in batches:
                    for line in batch_result['lines']:
                        new_batches.append({
                            **batch_result,
                            'payment_values': {
                                **batch_result['payment_values'],
                                'payment_type': 'inbound' if line.balance > 0 else 'outbound'
                            },
                            'lines': line,
                        })
                batches = new_batches

            for batch_result in batches:
                to_process.append({
                    'create_vals': self._create_payment_vals_from_batch(batch_result),
                    'to_reconcile': batch_result['lines'],
                    'batch': batch_result,
                })

        # Paso 1: Crear pagos
        payments = self._init_payments(to_process, edit_mode=edit_mode)

        # Paso 2: Postear
        self._post_payments(to_process, edit_mode=edit_mode)

        # Paso 3: Conciliar
        self._reconcile_payments(to_process, edit_mode=edit_mode)

        # Paso 4: Forzar residual y estado en la factura (SQL)
        move_ids = self.env.context.get('active_ids', []) if self.env.context.get('active_model') == 'account.move' else []
        for move in self.env['account.move'].browse(move_ids):
            pagado = self.amount
            total = move.amount_total
            nuevo_residual = move.company_currency_id.round(total - pagado)

            estado = 'paid' if move.company_currency_id.is_zero(nuevo_residual) else 'partial'

            self.env.cr.execute("""
                UPDATE account_move
                SET amount_residual = %s,
                    invoice_payment_state = %s
                WHERE id = %s
            """, (nuevo_residual, estado, move.id))

        return payments