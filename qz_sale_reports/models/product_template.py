from odoo import _, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    customisation = fields.Boolean(string="Customisation ?")
