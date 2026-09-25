import base64

from odoo import models
from odoo.tools.safe_eval import safe_eval, time


class MailTemplate(models.Model):
    _inherit = 'mail.template'

    def _generate_template_attachments(self, res_ids, render_fields, render_results=None):
        self.ensure_one()
        standard = self.env.ref('sale.action_report_saleorder')
        replace_order = (
            self.model == 'sale.order' and 'report_template_ids' in render_fields
            and standard in self.report_template_ids
        )
        offsets = {
            record_id: len((render_results or {}).get(record_id, {}).get('attachments', []))
            for record_id in res_ids
        }
        results = super()._generate_template_attachments(
            res_ids, render_fields, render_results=render_results,
        )
        if not replace_order:
            return results
        for order in self.env['sale.order'].browse(res_ids):
            filename = (
                safe_eval(standard.print_report_name, {'object': order, 'time': time})
                if standard.print_report_name else self.env._('Report')
            )
            if not filename.endswith('.pdf'):
                filename += '.pdf'
            attachments = results[order.id].get('attachments', [])
            for index in range(offsets[order.id], len(attachments)):
                if attachments[index][0] == filename:
                    attachments[index:index + 1] = [
                        (name, base64.b64encode(content))
                        for name, content in order._qz_signed_attachments()
                    ]
                    break
        return results
