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
        domain=[("sale_ok", "=", True)],
        help="Busca por nombre o referencia interna (default_code).",
    )

    default_code = fields.Char(
        string="Referencia interna",
        readonly=True,
    )

    price_net = fields.Monetary(
        string="Precio Neto",
        currency_field="currency_id",
        readonly=True,
    )

    price_gross = fields.Monetary(
        string="Precio + IVA (19%)",
        currency_field="currency_id",
        readonly=True,
    )

    qty_available = fields.Float(
        string="Cantidad a mano",
        readonly=True,
        digits="Product Unit of Measure",
    )

    @api.onchange("product_id")
    def _onchange_product_id(self):
        for w in self:
            if w.product_id:
                tmpl = w.product_id.product_tmpl_id
                neto = tmpl.list_price
                w.price_net = neto
                w.price_gross = neto * 1.19
                w.qty_available = w.product_id.qty_available
                w.default_code = w.product_id.default_code or ""
            else:
                w.price_net = 0.0
                w.price_gross = 0.0
                w.qty_available = 0.0
                w.default_code = ""
