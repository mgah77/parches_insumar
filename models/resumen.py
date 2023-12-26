from odoo import models, fields , api,  _

class Resumen(models.Model):

    _name = 'taller.resumen'
    _description = 'Resumen'

    recibidas = fields.Integer('Recibidas', readonly=True)
    por_pagar = fields.Integer('Por Pagar')

    @api.model
    def _compute_recibidas(self):
        temp = self.env['account.move'].search_count([('move_type','=','in_invoice'),('payment_state','=','not_paid')])      
        for record in self:                    
            record.recibidas = temp
        return    