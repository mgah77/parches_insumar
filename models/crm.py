from odoo import models, fields

class Crm_team_mail(models.Model):
    _inherit = 'crm.team'

    mail_team = fields.char(string ='Team e-mail')