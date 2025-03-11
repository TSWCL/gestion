from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class AnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

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
    salesman_id = fields.Many2one(
        'res.users',
        string="Vendedor",
        compute='_compute_sale_order_from_lines',
        store=True
    )
    total_debit = fields.Monetary(
        string="Total Débito",
        compute="_compute_totals",
        store=True
    )
    total_credit = fields.Monetary(
        string="Total Crédito",
        compute="_compute_totals",
        store=True
    )
    total_balance = fields.Monetary(
        string="Total Balance",
        compute="_compute_totals",
        store=True
    )
    currency_id = fields.Many2one(
        'res.currency',
        string="Moneda",
        default=lambda self: self.env.company.currency_id
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

    @api.depends('sale_order_id.order_line.analytic_distribution', 'sale_order_id.order_line.product_id')
    def _compute_sale_order_from_lines(self):
        """
        Relaciona la cuenta analítica con la orden de venta basada en `sale.order.line.analytic_distribution`.
        También actualiza el vendedor y el cliente basado en la orden de venta encontrada.
        """
        for rec in self:
            sale_order = False

            # Buscar líneas de venta donde analytic_distribution contenga la cuenta analítica
            sale_lines = self.env['sale.order.line'].search([
                ('analytic_distribution', '!=', False)
            ])

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

    ###  NUEVO: Método para forzar actualización global
    def _update_analytic_sales_links(self):
        """
        Recalcula las órdenes de venta asociadas a las cuentas analíticas.
        """
        self.env['account.analytic.account'].search([])._compute_sale_order_from_lines()

    @api.depends('total_debit', 'total_credit')
    def _compute_totals(self):
        """
        Calcula los débitos, créditos y balance desde `account.move.line`,
        utilizando `analytic_distribution` como referencia.
        """
        for record in self:
            total_debit = 0.0
            total_credit = 0.0

            # Buscar líneas contables con distribución analítica que contengan esta cuenta
            move_lines = self.env['account.move.line'].search([
                ('analytic_distribution', '!=', False)
            ])

            for line in move_lines:
                analytic_data = line.analytic_distribution  # Es un diccionario con IDs de cuentas analíticas

                if str(record.id) in analytic_data:
                    total_debit += line.debit
                    total_credit += line.credit

            # Guardar valores en los campos
            record.total_debit = total_debit
            record.total_credit = total_credit
            record.total_balance = total_credit - total_debit

    ###  NUEVO: Forzar actualización cada vez que se modifica una factura
    @api.depends('sale_order_id.invoice_ids.invoice_line_ids')
    def _compute_profit_margin(self):
        """
        Calcula el margen de ganancia en base a las facturas asociadas a la cuenta analítica.
        """
        for rec in self:
            total_revenue = 0
            total_costs = 0

            # Buscar facturas de venta vinculadas a la cuenta analítica
            invoices = self.env['account.move'].search([
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
                ('invoice_line_ids.analytic_distribution', '!=', False)
            ])

            # Calcular ingresos desde las líneas de factura
            for invoice in invoices:
                for line in invoice.invoice_line_ids:
                    analytic_data = line.analytic_distribution
                    if analytic_data and str(rec.id) in analytic_data:
                        total_revenue += line.price_subtotal  # Se suma directamente el subtotal

            # Buscar costos en las líneas contables asociadas a la cuenta analítica
            cost_lines = self.env['account.move.line'].search([
                ('account_id.internal_group', '=', 'expense'),
                ('parent_state', '=', 'posted'),
                ('analytic_distribution', '!=', False)
            ])

            for cost in cost_lines:
                analytic_data = cost.analytic_distribution
                if analytic_data and str(rec.id) in analytic_data:
                    total_costs += cost.debit  # Se suma directamente el costo

            # Cálculo de margen de ganancia
            rec.revenue = total_revenue
            rec.costs = total_costs
            rec.profit_margin = total_revenue - total_costs
            rec.profit_margin_percentage = (rec.profit_margin / total_revenue * 100) if total_revenue > 0 else 0

            _logger.info("Cuenta Analítica '%s': Ingresos = %s, Costos = %s, Margen = %s (%s%%)",
                         rec.name, total_revenue, total_costs, rec.profit_margin, rec.profit_margin_percentage)

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _trigger_analytic_updates(self):
        """Forzar actualización de totales y márgenes."""
        self.env['account.analytic.account'].search([])._compute_totals()
        self.env['account.analytic.account'].search([])._compute_profit_margin()

    def write(self, vals):
        result = super().write(vals)
        self._trigger_analytic_updates()
        return result

    def create(self, vals):
        record = super().create(vals)
        self._trigger_analytic_updates()
        return record

    def unlink(self):
        result = super().unlink()
        self._trigger_analytic_updates()
        return result
class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    ###  NUEVO: Se ejecuta cada vez que se cambia `analytic_distribution`
    @api.onchange('analytic_distribution')
    def _onchange_analytic_distribution(self):
        """
        Cuando cambia la distribución analítica, actualiza la cuenta analítica vinculada.
        """
        if self.analytic_distribution:
            self.env['account.analytic.account']._update_analytic_sales_links()

    ###  TRIGGERS PARA ACTUALIZAR AUTOMÁTICAMENTE ###
    def write(self, vals):
        """
        Detecta cualquier cambio en `sale.order.line` y actualiza las cuentas analíticas relacionadas.
        """
        result = super().write(vals)
        self.env['account.analytic.account']._update_analytic_sales_links()
        return result

    def create(self, vals):
        """
        Detecta la creación de nuevas `sale.order.line` y actualiza las cuentas analíticas relacionadas.
        """
        record = super().create(vals)
        self.env['account.analytic.account']._update_analytic_sales_links()
        return record

    def unlink(self):
        """
        Detecta la eliminación de `sale.order.line` y actualiza las cuentas analíticas relacionadas.
        """
        result = super().unlink()
        self.env['account.analytic.account']._update_analytic_sales_links()
        return result
