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


    def action_create_payments(self):
        payments = self._create_payments()

        if self._context.get('dont_redirect_to_payments'):
            return True

        for wizard in self:
            if wizard.env.context.get('active_model') == 'account.move':
                move_ids = wizard.env.context.get('active_ids', [])
                for move in wizard.env['account.move'].browse(move_ids):
                    pagado = wizard.amount
                    total = move.amount_total
                    nuevo_residual = move.company_currency_id.round(total - pagado)

                    # Por defecto: estado parcial
                    payment_state = 'partial'

                    # Si pagado cubre total (dentro de margen de error), marcar como pagado
                    if move.company_currency_id.is_zero(nuevo_residual):
                        payment_state = 'paid'

                    # Actualizar por SQL solo la factura
                    self.env.cr.execute("""
                        UPDATE account_move
                        SET amount_residual = %s,
                            invoice_payment_state = %s
                        WHERE id = %s
                    """, (nuevo_residual, payment_state, move.id))

        return {
            'name': _('Payments'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'context': {'create': False},
            'view_mode': 'form' if len(payments) == 1 else 'tree,form',
            'res_id': payments.id if len(payments) == 1 else False,
            'domain': [('id', 'in', payments.ids)] if len(payments) > 1 else [],
        }