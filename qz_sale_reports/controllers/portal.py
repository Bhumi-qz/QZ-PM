from odoo import http
from odoo.exceptions import AccessError, MissingError
from odoo.http import request
from odoo.addons.sale.controllers.portal import CustomerPortal


class QzDocumentPortal(CustomerPortal):
    @http.route('/my/orders/<int:order_id>/qz-document/<string:document>',
                type='http', auth='public', website=True)
    def qz_document(self, order_id, document, access_token=None, **kwargs):
        reports = {
            'proposal': 'qz_sale_reports.action_report_sale_proposal',
            'amc': 'qz_sale_reports.action_report_amc',
        }
        if document not in reports:
            return request.not_found()
        try:
            order = self._document_check_access('sale.order', order_id, access_token)
        except (AccessError, MissingError):
            return request.not_found()
        if document == 'amc' and not order.qz_add_amc:
            return request.not_found()
        return self._show_report(order, 'pdf', reports[document], download=False)

    @http.route()
    def portal_quote_accept(self, order_id, access_token=None, name=None, signature=None):
        request.update_context(qz_accept_order_id=order_id)
        return super().portal_quote_accept(
            order_id, access_token=access_token, name=name, signature=signature,
        )
