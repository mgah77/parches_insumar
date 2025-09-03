# -*- coding: utf-8 -*-
from odoo import api, fields, models

class PriceCheckWizard(models.TransientModel):
    _name = "price.check.wizard"
    _description = "Consulta de Precios"

    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
        required=True,
        readonly=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        related="company_id.currency_id",
        store=False,
        readonly=True,
    )

    product_id = fields.Many2one(
        "product.product",
        string="Producto",
        required=True,
        help="Busca por nombre o referencia interna (default_code).",
        domain=[("sale_ok", "=", True)],
    )

    list_price = fields.Monetary(
        string="Precio de venta",
        currency_field="currency_id",
        readonly=True,
    )

    qty_available = fields.Float(
        string="Cantidad a mano",
        readonly=True,
        digits="Product Unit of Measure",
    )

    default_code = fields.Char(
        string="Referencia interna",
        readonly=True,
    )

    @api.onchange("product_id")
    def _onchange_product_id(self):
        for w in self:
            if w.product_id:
                tmpl = w.product_id.product_tmpl_id
                w.list_price = tmpl.list_price
                w.qty_available = w.product_id.qty_available
                w.default_code = w.product_id.default_code or ""
            else:
                w.list_price = 0.0
                w.qty_available = 0.0
                w.default_code = ""
