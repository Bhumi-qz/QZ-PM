from odoo import fields, models


class Project(models.Model):
    _inherit = "project.project"

    hourly_rate = fields.Float(string="Project Hourly Rate")
    hourly_rate_text = fields.Text(string="Hourly Rate")