from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)
class AnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    salesman_id = fields.Many2one(
        'res.users',
        string="Vendedor",
        help="Vendedor asignado a la orden de venta relacionada con esta cuenta analítica."
    )
    sale_order_id = fields.Many2one(
        'sale.order',
        string="Orden de Venta",
        compute='_compute_sale_order_from_lines',
        store=True
    )
    partner_id = fields.Many2one(
        'res.partner',
        string="Cliente",
        compute='_compute_sale_order_from_lines',
        store=True
    )
    total_debit = fields.Float(
        string="Total Débito",
        compute="_compute_totals",
        store=True
    )
    total_credit = fields.Float(
        string="Total Crédito",
        compute="_compute_totals",
        store=True
    )
    total_balance = fields.Float(
        string="Total Balance",
        compute="_compute_totals",
        store=True
    )

    @api.depends('debit', 'credit', 'balance')
    def _compute_totals(self):
        for record in self:
            record.total_debit = record.debit
            record.total_credit = record.credit
            record.total_balance = record.balance

    @api.depends('name')
    def _compute_sale_order_from_lines(self):
        """
        Relaciona la cuenta analítica con la orden de venta basada en `sale.order.line.analytic_distribution`.
        También actualiza el vendedor y el cliente basado en la orden de venta encontrada.
        """
        for rec in self:
            sale_order = False

            # Buscar líneas de venta donde analytic_distribution contenga la cuenta analítica
            sale_lines = self.env['sale.order.line'].search([('analytic_distribution', '!=', False)])

            for line in sale_lines:
                distribution = line.analytic_distribution  

                if not isinstance(distribution, dict):
                    _logger.error("Error: analytic_distribution en línea %s no es un diccionario: %s", line.id, type(distribution))
                    continue

                if str(rec.id) in distribution:
                    sale_order = line.order_id
                    _logger.info("Cuenta analítica '%s' vinculada a orden de venta '%s'", rec.name, sale_order.name)
                    break  

            if sale_order:
                rec.sale_order_id = sale_order.id
                rec.partner_id = sale_order.partner_id.id
                rec.salesman_id = sale_order.user_id.id 
                _logger.info("Cuenta analítica '%s' actualizada con orden de venta '%s' y vendedor '%s'",
                             rec.name, sale_order.name, sale_order.user_id.name)
            else:
                rec.sale_order_id = False
                rec.partner_id = False
                rec.salesman_id = False
                _logger.info("No se encontró una orden de venta para la cuenta analítica '%s'", rec.name)