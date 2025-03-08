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
    revenue = fields.Monetary(
        string="Ingresos",
        compute="_compute_profit_margin",
        store=True
    )
    costs = fields.Monetary(
        string="Costos",
        compute="_compute_profit_margin",
        store=True
    )
    profit_margin = fields.Monetary(
        string="Margen de Ganancia",
        compute="_compute_profit_margin",
        store=True
    )
    profit_margin_percentage = fields.Float(
        string="Margen de Ganancia (%)",
        compute="_compute_profit_margin",
        store=True
    )
    currency_id = fields.Many2one("res.currency", string="Moneda", default=lambda self: self.env.company.currency_id)

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

    @api.depends('name')
    def _compute_profit_margin(self):
        """
        Calcula el margen de ganancia en base a las facturas finales asociadas a la cuenta analítica.
        """
        for rec in self:
            total_revenue = 0
            total_costs = 0

            # Buscar todas las facturas de venta
            invoices = self.env['account.move'].search([
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted')  # Solo facturas validadas
            ])

            # Buscar las líneas de factura y filtrar por `analytic_distribution`
            for invoice in invoices:
                for line in invoice.invoice_line_ids:
                    analytic_data = line.analytic_distribution
                    if analytic_data and str(rec.id) in analytic_data:
                        total_revenue += line.price_subtotal  # Se suma el subtotal sin impuestos

            # Buscar costos en las líneas de factura
            cost_lines = self.env['account.move.line'].search([
                ('account_id.internal_group', '=', 'expense'),
                ('parent_state', '=', 'posted')  # Solo costos confirmados
            ])

            for cost in cost_lines:
                analytic_data = cost.analytic_distribution
                if analytic_data and str(rec.id) in analytic_data:
                    total_costs += cost.debit  # Se suma el costo (cargos)

            # Cálculo de margen de ganancia
            rec.revenue = total_revenue
            rec.costs = total_costs
            rec.profit_margin = total_revenue - total_costs
            rec.profit_margin_percentage = (rec.profit_margin / total_revenue * 100) if total_revenue > 0 else 0

            _logger.info("Cuenta Analítica '%s': Ingresos = %s, Costos = %s, Margen = %s (%s%%)",
                         rec.name, total_revenue, total_costs, rec.profit_margin, rec.profit_margin_percentage)