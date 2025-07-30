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

        # ⚠️ Capturar valores originales de las facturas
        original_amounts = {}
        move_ids = self.env.context.get('active_ids', []) if self.env.context.get('active_model') == 'account.move' else []
        for move in self.env['account.move'].browse(move_ids):
            original_amounts[move.id] = move.amount_total

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

        # Paso 2: Publicar pagos
        self._post_payments(to_process, edit_mode=edit_mode)

        # Paso 3: Conciliar
        self._reconcile_payments(to_process, edit_mode=edit_mode)

        # Paso 4: Forzar residual y estado de pago (payment_state) en la factura
        for move in self.env['account.move'].browse(move_ids):
            total = original_amounts.get(move.id, 0.0)
            pagado = self.amount
            nuevo_residual = move.company_currency_id.round(total - pagado)
            estado = 'paid' if nuevo_residual == 0.0 else 'partial'

            self.env.cr.execute("""
                UPDATE account_move
                SET amount_residual = %s,
                    payment_state = %s
                WHERE id = %s
            """, (nuevo_residual, estado, move.id))

        return payments