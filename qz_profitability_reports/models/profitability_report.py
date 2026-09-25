from odoo import api, fields, models, tools


class ProfitabilityReport(models.Model):
    """One report row per project timesheet line with an employee.

    Project revenue is allocated hours times project rate, counted once.
    Distribute it over eligible timesheets by signed hours so customer,
    consultant and drill-down totals reconcile. Zero-net-hour projects use
    equal shares. Date filters select those shares, not a second full budget.
    """
    _name = 'profitability.report'
    _description = "Profitability Report"
    _auto = False
    _order = 'date desc'

    employee_id = fields.Many2one('hr.employee', string="Consultant", readonly=True)
    project_id = fields.Many2one('project.project', string="Project", readonly=True)
    partner_id = fields.Many2one('res.partner', string="Customer", readonly=True)
    company_id = fields.Many2one('res.company', string="Company", readonly=True)
    date = fields.Date(string="Date", readonly=True)
    timesheet_id = fields.Many2one('account.analytic.line', string="Timesheet", readonly=True)
    hours = fields.Float(string="Hours", readonly=True, aggregator='sum')
    hourly_rate = fields.Float(string="Billing Rate/hr", readonly=True, aggregator='avg')
    hourly_cost = fields.Float(string="Cost/hr", readonly=True, aggregator='avg')
    revenue = fields.Float(string="Revenue", readonly=True, aggregator='sum',
                           help="This entry's share of allocated project hours × project rate. "
                                "All project entries together count the project revenue once.")
    cost = fields.Float(string="Cost", readonly=True, aggregator='sum')
    profit = fields.Float(string="Profit", readonly=True, aggregator='sum')

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(f"""
            CREATE VIEW {self._table} AS (
                WITH amounts AS (
                SELECT
                    l.id AS id,
                    l.id AS timesheet_id,
                    l.employee_id AS employee_id,
                    l.project_id AS project_id,
                    pr.partner_id AS partner_id,
                    l.company_id AS company_id,
                    l.date AS date,
                    l.unit_amount AS hours,
                    COALESCE(pr.hourly_rate, 0.0) AS hourly_rate,
                    COALESCE(e.hourly_cost, 0.0) AS hourly_cost,
                    COALESCE(pr.allocated_hours, 0.0) * COALESCE(pr.hourly_rate, 0.0)
                    * CASE WHEN SUM(COALESCE(l.unit_amount, 0.0)) OVER (PARTITION BY pr.id) != 0
                        THEN COALESCE(l.unit_amount, 0.0)
                             / SUM(COALESCE(l.unit_amount, 0.0)) OVER (PARTITION BY pr.id)
                        ELSE 1.0 / COUNT(*) OVER (PARTITION BY pr.id)
                      END AS revenue,
                    COALESCE(l.unit_amount, 0.0) * COALESCE(e.hourly_cost, 0.0) AS cost
                FROM account_analytic_line l
                JOIN project_project pr ON pr.id = l.project_id
                JOIN hr_employee e ON e.id = l.employee_id
                WHERE l.project_id IS NOT NULL
                  AND l.employee_id IS NOT NULL
                )
                SELECT amounts.*, revenue - cost AS profit FROM amounts
            )
        """)

    def action_open_timesheet(self):
        self.ensure_one()
        self.check_access('read')
        self.timesheet_id.check_access('read')
        return {
            'type': 'ir.actions.act_window', 'name': 'Timesheet',
            'res_model': 'account.analytic.line', 'res_id': self.timesheet_id.id,
            'views': [(False, 'form')], 'target': 'current',
        }

    @api.model
    def get_customer_dashboard_data(self, domain=None):
        """Use the native dashboard filter domain and count each project budget once.

        Allocations are the full project budgets for projects represented by the
        filtered timesheets, not a prorated budget for the selected period.
        Revenue sums the project-budget shares of the filtered timesheets.
        Cost is hours times the employee's current hourly cost.
        """
        grouped = self._read_group(
            list(domain or []) + [('partner_id', '!=', False)],
            groupby=['partner_id', 'project_id'],
            aggregates=['hours:sum', 'revenue:sum', 'cost:sum', 'profit:sum'],
        )
        customers = {}
        for partner, project, hours, revenue, cost, profit in grouped:
            row = customers.setdefault(partner.id, {
                'id': partner.id, 'name': partner.display_name,
                'planned': 0.0, 'hours': 0.0, 'revenue': 0.0,
                'cost': 0.0, 'profit': 0.0,
            })
            # Grouping by project makes this addition independent of timesheet count.
            row['planned'] += project.allocated_hours if project else 0.0
            row['hours'] += hours or 0.0
            row['revenue'] += revenue or 0.0
            row['cost'] += cost or 0.0
            row['profit'] += profit or 0.0
        rows = list(customers.values())
        for row in rows:
            row['margin'] = row['profit'] / row['revenue'] * 100 if row['revenue'] else 0.0
            row['variance'] = row['planned'] - row['hours']
        rows.sort(key=lambda row: (-row['profit'], row['name']))
        totals = {key: sum(row[key] for row in rows)
                  for key in ('planned', 'hours', 'revenue', 'cost', 'profit')}
        totals['customers'] = len(rows)
        totals['margin'] = totals['profit'] / totals['revenue'] * 100 if totals['revenue'] else 0.0
        currency = self.env.company.currency_id
        return {
            'rows': rows, 'totals': totals,
            'currency': {'name': currency.name, 'digits': currency.decimal_places},
        }

    @api.model
    def get_dashboard_data(self, date_from=False, date_to=False, top_n=5, domain=None):
        """Aggregate timesheet-derived profitability per consultant, for the
        KPI dashboard. Returns plain JSON-serializable data.
        """
        domain = list(domain or [])
        if date_from:
            domain.append(('date', '>=', date_from))
        if date_to:
            domain.append(('date', '<=', date_to))

        grouped = self._read_group(
            domain,
            groupby=['employee_id'],
            aggregates=['hours:sum', 'revenue:sum', 'cost:sum', 'profit:sum'],
        )

        consultants = []
        total_hours = total_revenue = total_cost = total_profit = 0.0
        for employee, hours, revenue, cost, profit in grouped:
            if not employee:
                continue
            hours = hours or 0.0
            revenue = revenue or 0.0
            cost = cost or 0.0
            profit = profit or 0.0
            total_hours += hours
            total_revenue += revenue
            total_cost += cost
            total_profit += profit
            consultants.append({
                'id': employee.id,
                'name': employee.name,
                'hours': hours,
                'revenue': revenue,
                'cost': cost,
                'profit': profit,
                'revenue_per_hour': revenue / hours if hours else 0.0,
                'cost_per_hour': cost / hours if hours else 0.0,
                'profit_per_hour': profit / hours if hours else 0.0,
            })

        consultants.sort(key=lambda c: c['profit'], reverse=True)
        margin = (total_profit / total_revenue * 100.0) if total_revenue else 0.0

        currency = self.env.company.currency_id

        return {
            'kpi': {
                'total_consultants': len(consultants),
                'total_hours': total_hours,
                'total_revenue': total_revenue,
                'total_cost': total_cost,
                'total_profit': total_profit,
                'margin': margin,
            },
            'top_consultants': consultants[:top_n],
            'consultants': consultants,
            'currency': {
                'name': currency.name,
                'digits': currency.decimal_places,
                'symbol': currency.symbol,
                'position': currency.position,
            },
        }
