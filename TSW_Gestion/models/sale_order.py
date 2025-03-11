from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def write(self, vals):
        """
        Si cambian el cliente (`partner_id`) o el vendedor (`user_id`),
        también se actualizará la cuenta analítica asociada a la orden de venta.
        """
        res = super(SaleOrder, self).write(vals)

        # Verificamos si cambió el cliente o el vendedor
        if 'partner_id' in vals or 'user_id' in vals:
            for order in self:
                analytic_account = self.env['account.analytic.account'].search([
                    ('sale_order_id', '=', order.id)
                ], limit=1)

                if analytic_account:
                    updates = {}
                    if 'partner_id' in vals:
                        updates['partner_id'] = order.partner_id.id
                    if 'user_id' in vals:
                        updates['salesman_id'] = order.user_id.id

                    analytic_account.write(updates)

                    _logger.info("Cuenta analítica '%s' actualizada con Cliente '%s' y Vendedor '%s'", 
                                 analytic_account.name, 
                                 order.partner_id.name, 
                                 order.user_id.name)
        
        return res