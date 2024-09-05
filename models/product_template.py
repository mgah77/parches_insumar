from odoo import models, fields

class ProductDepartment(models.Model):
    _inherit = 'product.template'  # Reemplaza 'your.model' por el nombre del modelo que deseas modificar

    # Modifica el campo partner_id para agregar un filtro adicional
    depto = fields.Selection([
                            ('Inspeccion de balsa','Inspeccion de balsa'),
                            ('Contenedores','Contenedores'),
                            ('Válvulas','Válvulas'),
                            ('Exintores','Exintores'),
                            ('Equipos de seguridad','Equipos de seguridad'),
                            ('Banco CO2','Banco CO2'),
                            ('Textil','Textil')
    ])
