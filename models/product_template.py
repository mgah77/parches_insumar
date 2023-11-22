from odoo import models, fields

class ProductDepartment(models.Model):
    _inherit = 'product.template'  # Reemplaza 'your.model' por el nombre del modelo que deseas modificar

    # Modifica el campo partner_id para agregar un filtro adicional
    depto = fields.Selection([
                            ('bals','Inspeccion de balsa'),
                            ('cont','Contenedores'),
                            ('valv','Válvulas'),
                            ('exti','Exintores'),
                            ('segu','Equipos de seguridad'),
                            ('bco2','Banco CO2'),
                            ('text','Textil')
    ])
