from odoo import models, fields

class IrUiMenu(models.Model):
    _inherit = 'ir.ui.menu'

    require_has_reparos = fields.Boolean(
        string="Ocultar si compañía no tiene reparos",
        default=False,
    )

    def _filter_visible_menus(self):
        menus = super()._filter_visible_menus()
        # Si la compañía activa NO tiene reparos, quitamos todos los marcados
        if not self.env.company.has_reparos:
            menus = menus.filtered(lambda m: not m.require_has_reparos)
        return menus