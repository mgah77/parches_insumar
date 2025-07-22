from odoo import models, fields

class CrmTeam(models.Model):
    _inherit = 'crm.team'

    mail = fields.Char(string="Correo del equipo")