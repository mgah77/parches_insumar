from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    payment_form = fields.Selection([
        ('EFE','Efectivo'),
        ('TAR','Tarjeta de Credito'),
        ('DEB','Debito'),
        ('TRA','Transferencia'),
        ('DEP','Deposito'),
        ('CHE','Cheque'),
        ('CRE','Credito'),
        ('RE','Regularización'),
        ] , required="True")