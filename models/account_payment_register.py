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