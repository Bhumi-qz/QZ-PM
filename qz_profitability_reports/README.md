# Profitability Dashboard

Odoo 19 customer and consultant profitability dashboards. Technical module:
`qz_profitability_reports`, version **19.0.2.12.0**.

## Current calculation

- Revenue = project allocated hours × project hourly rate, counted once per project.
- Cost = logged timesheet hours × the employee's current hourly cost.
- Profit = revenue − cost.
- Margin = profit / revenue × 100, shown to two decimals (0% when revenue is zero).

Example: allocated 600 hours at 110.17 gives revenue **66,102.00**. Logged
127.15 hours at employee cost 32 gives cost **4,068.80**, profit **62,033.20**
and margin **93.84%**.

Both dashboards and the detail action default to **all time**. The KPI label is
**Revenue**.

## Consultant and date allocation

The SQL view contains one row per timesheet with a project and employee. Project
revenue is distributed in proportion to signed logged hours over all eligible
entries. Zero-net-hour projects use equal shares. This makes customer totals,
consultant totals and clickable detail sums agree without duplicating the budget.

A selected date or employee filter shows the corresponding revenue shares and
costs. Planned hours remain the full allocations of projects represented by the
filtered entries. Projects without eligible timesheets are not included.
Customer reporting additionally requires a project customer.

Stored source-timesheet revenue remains a separate hourly calculation. The
profitability report calculates project-budget revenue directly and does not
depend on stale stored timesheet revenue/cost. Current rates are used, without
historical snapshots. This is project-budget profitability, not invoice-based
accounting profit.

## Navigation

- Names open customer or employee forms.
- Financial amounts, margins, spent hours, variances and chart bars open filtered detail rows.
- Planned hours open contributing projects; count cards open represented records.
- Detail forms link to customer, employee, project and source timesheet.
- Detail lists have an Open Timesheet button; pivot cells support drill-down.
- All dashboard controls support keyboard focus and activation; normal record access applies.

## Usage

Open Dashboards → Human Resources → Customer-wise or Consultant-wise.
