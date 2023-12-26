from odoo import models, fields , api,  _

class Resumen(models.Model):

    _name = 'taller.resumen'
    _description = 'Resumen'

    recibidas = fields.Integer('Recibidas')
    por_pagar = fields.Integer('Por Pagar')

    @api.model
    def _compute_recibidas(self):
        temp = 0        
        for record in self:
            temp = self.env['account.move'].search([('move_type','=','in_invoice'),('payment_state','=','not_paid')])           
            record.recibidas = len(temp)
        return    