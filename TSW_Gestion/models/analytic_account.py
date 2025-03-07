from odoo import models, fields, api

class AnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    salesman_id = fields.Many2one(
        comodel_name='res.users',
        string='Vendedor',
        domain=[('share', '=', False)]
    )

class AnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

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
            # Lógica de cómputo; este es solo un ejemplo básico.
            record.total_debit = record.debit
            record.total_credit = record.credit
            record.total_balance = record.balance