from odoo import models, fields , api,  _

class Resumen(models.Model):

    _name = 'taller.resumen'
    _description = 'Resumen'

    recibidas = fields.Integer('Recibidas', readonly=True, compute="_compute_recibidas")
    por_pagar = fields.Integer('Por Pagar')

    
    def _compute_recibidas(self):
        temp = self.env['account.move'].search_count([('move_type','=','in_invoice')])      
        for record in self:                    
            record.recibidas = temp
        return    