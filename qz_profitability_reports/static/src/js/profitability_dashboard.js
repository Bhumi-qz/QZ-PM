/** @odoo-module **/

import { Component, onWillStart, onWillUnmount, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { Domain } from "@web/core/domain";
import { SpreadsheetDashboardAction } from "@spreadsheet_dashboard/bundle/dashboard_action/dashboard_action";

export class QzCustomerDashboard extends Component {
    static template = "qz_profitability.CustomerDashboard";
    static props = { model: Object };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({ loading: true, error: "", data: null });
        this.request = 0;
        this.destroyed = false;
        this.domainKey = null;
        this.update = () => this.load();
        this.props.model.on("update", this, this.update);
        onWillStart(() => this.load());
        onWillUnmount(() => {
            this.destroyed = true;
            this.request++;
            this.props.model.off("update", this, this.update);
        });
    }

    async load(force = false) {
        const domain = this.props.model.getters.getPivotComputedDomain(this.pivotId);
        const key = JSON.stringify(domain);
        if (!force && key === this.domainKey) {
            return;
        }
        this.domainKey = key;
        const request = ++this.request;
        this.state.loading = true;
        this.state.error = "";
        try {
            const data = await this.orm.call(
                "profitability.report", this.rpcMethod, [], { domain }
            );
            if (!this.destroyed && request === this.request) {
                this.state.data = this.prepareData(data);
                this.loadedDomain = domain;
            }
        } catch (error) {
            if (!this.destroyed && request === this.request) {
                this.state.data = null;
                this.state.error = _t("Could not load profitability. Please retry or check your report access.");
                this.domainKey = null;
            }
        } finally {
            if (!this.destroyed && request === this.request) {
                this.state.loading = false;
            }
        }
    }

    get pivotId() { return "1"; }
    get rpcMethod() { return "get_customer_dashboard_data"; }
    get groupField() { return "partner_id"; }
    get recordModel() { return "res.partner"; }
    prepareData(data) { return data; }

    detailDomain(row) {
        return Domain.and([
            this.loadedDomain || [],
            this.groupField === "partner_id" ? [["partner_id", "!=", false]] : [],
            row ? [[this.groupField, "=", row.id]] : [],
        ]).toList();
    }

    openDetails(row) {
        return this.action.doAction({
            type: "ir.actions.act_window", name: _t("Profitability Details"),
            res_model: "profitability.report", views: [[false, "list"], [false, "form"], [false, "pivot"], [false, "graph"]],
            domain: this.detailDomain(row), target: "current",
        });
    }

    openRecord(row) {
        return this.action.doAction({
            type: "ir.actions.act_window", name: row.name,
            res_model: this.recordModel, res_id: row.id,
            views: [[false, "form"]], target: "current",
        });
    }

    async openProjects(row) {
        const groups = await this.orm.call("profitability.report", "read_group", [], {
            domain: this.detailDomain(row), fields: ["project_id"], groupby: ["project_id"],
        });
        return this.action.doAction({
            type: "ir.actions.act_window", name: _t("Projects"),
            res_model: "project.project", views: [[false, "list"], [false, "form"]],
            domain: [["id", "in", groups.filter((group) => group.project_id).map((group) => group.project_id[0])]],
            target: "current",
        });
    }

    openRecords() {
        return this.action.doAction({
            type: "ir.actions.act_window", name: _t("Profitability Records"),
            res_model: this.recordModel, views: [[false, "list"], [false, "form"]],
            domain: [["id", "in", this.state.data.rows.map((row) => row.id)]], target: "current",
        });
    }

    get topCustomers() {
        return (this.state.data?.rows || []).filter((row) => row.profit > 0).slice(0, 5);
    }

    get lossCustomers() {
        return (this.state.data?.rows || []).filter((row) => row.profit < 0)
            .sort((a, b) => a.profit - b.profit);
    }

    number(value, digits = 2) {
        return new Intl.NumberFormat(undefined, {
            minimumFractionDigits: 0, maximumFractionDigits: digits,
        }).format(value || 0);
    }

    money(value) {
        return this.number(value, this.state.data?.currency.digits ?? 2);
    }

    tone(value) {
        return value < 0 ? "qz-negative" : value > 0 ? "qz-positive" : "";
    }

    barWidth(row) {
        const maximum = this.topCustomers[0]?.profit || 1;
        return `width: ${Math.max(0, Math.min(100, row.profit / maximum * 100))}%`;
    }
}

export class QzConsultantDashboard extends QzCustomerDashboard {
    static template = "qz_profitability.ConsultantDashboard";

    get pivotId() { return "2"; }
    get rpcMethod() { return "get_dashboard_data"; }
    get groupField() { return "employee_id"; }
    get recordModel() { return "hr.employee"; }
    prepareData(data) {
        return {
            rows: data.consultants,
            currency: data.currency,
            totals: {
                consultants: data.kpi.total_consultants,
                hours: data.kpi.total_hours,
                revenue: data.kpi.total_revenue,
                cost: data.kpi.total_cost,
                profit: data.kpi.total_profit,
                margin: data.kpi.margin,
            },
        };
    }
}

patch(SpreadsheetDashboardAction, {
    components: { ...SpreadsheetDashboardAction.components, QzCustomerDashboard, QzConsultantDashboard },
});
