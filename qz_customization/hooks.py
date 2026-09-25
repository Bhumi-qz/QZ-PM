import logging

from lxml import etree

from odoo.tools import SQL
from odoo.tools.sql import column_exists, table_exists


_logger = logging.getLogger(__name__)


FIELD_COPY_MAP = [
    ("x_project_profitability_report", "x_actual_cost", "actual_cost"),
    ("x_project_profitability_report", "x_budget", "budget"),
    ("x_project_profitability_report", "x_hourly_cost", "hourly_cost"),
    ("x_project_profitability_report", "x_name", "name"),
    (
        "x_project_profitability_report",
        "x_profitability_pct",
        "profitability_pct",
    ),
    ("x_project_profitability_report", "x_project_id", "project_id"),

    # IMPORTANT:
    # Verify whether the target is really "maining_budget"
    # or should be "remaining_budget".
    (
        "x_project_profitability_report",
        "x_remaining_budget",
        "maining_budget",
    ),

    (
        "x_project_profitability_report",
        "x_snapshot_date",
        "snapshot_date",
    ),
    (
        "x_project_profitability_report",
        "x_total_hours",
        "total_hours",
    ),

    ("account_analytic_line", "x_cost", "cost"),
    ("account_analytic_line", "x_customer", "customer_id"),
    ("account_analytic_line", "x_employee_cost", "employee_cost"),
    (
        "account_analytic_line",
        "x_hourly_rate_text",
        "hourly_rate_text",
    ),
    (
        "account_analytic_line",
        "x_project_hourly_rate",
        "project_hourly_rate",
    ),
    (
        "account_analytic_line",
        "x_project_total_hours",
        "project_total_hours",
    ),
    ("account_analytic_line", "x_revenue", "revenue"),
    ("account_analytic_line", "x_plan2_id", "plan2_id"),

    ("project_project", "x_hourly_rate", "hourly_rate"),
    (
        "project_project",
        "x_hourly_rate_text",
        "hourly_rate_text",
    ),

    # ("budget_line", "x_plan2_id", "plan2_id"),
    # ("budget_report", "x_name", "name"),
    # ("budget_report", "x_plan2_id", "plan2_id"),
]


MODULES_TO_UNINSTALL = [
    "accountant",
    "timesheet_grid",
    "knowledge",
    "whatsapp",
    "helpdesk",
    "appointment",
    "sale_enterprise",
    "account_followup",
    "web_map",
    "account_reports",
    "mail_mobile",
    "product_barcodelookup",
    "ai",
    "currency_rate_live",
    "website_enterprise",
    "account_invoice_extract",
    "hr_recruitment_extract",
    "web_enterprise",
    "hr_recruitment_reports",
]


MODULES_TO_INSTALL = [
    "helpdesk_mgmt",
    "microsoft_outlook",
    "helpdesk_mgmt_project",
]


VIEWS_TO_ARCHIVE = [
    2128,
    1996,
]


MENUS_TO_ARCHIVE = [
    558,
    571,
    587,
]


ENTERPRISE_VIEW_TYPES = {
    "gantt",
    "grid",
    "cohort",
    "map",
}


FALLBACK_VIEW_MODE = "list,form"


# ============================================================
# Utility
# ============================================================


def _table_to_model(table_name):
    """
    Convert:
        account_analytic_line
    to:
        account.analytic.line
    """
    return table_name.replace("_", ".")


# ============================================================
# Copy old Studio field values
# ============================================================


def _copy_field_values(env):
    """
    Copy data from old Studio x_ fields into the new Python fields.
    """
    cr = env.cr

    for table, old_column, new_column in FIELD_COPY_MAP:

        if not table_exists(cr, table):
            _logger.warning(
                "Skipping %s.%s -> %s: table does not exist.",
                table,
                old_column,
                new_column,
            )
            continue

        if not column_exists(cr, table, old_column):
            _logger.warning(
                "Skipping %s.%s -> %s: source column does not exist.",
                table,
                old_column,
                new_column,
            )
            continue

        if not column_exists(cr, table, new_column):
            _logger.warning(
                "Skipping %s.%s -> %s: target column does not exist.",
                table,
                old_column,
                new_column,
            )
            continue

        cr.execute(
            SQL(
                """
                UPDATE %s
                   SET %s = %s
                 WHERE %s IS NOT NULL
                """,
                SQL.identifier(table),
                SQL.identifier(new_column),
                SQL.identifier(old_column),
                SQL.identifier(old_column),
            )
        )

        _logger.info(
            "Copied %s row(s): %s.%s -> %s.%s",
            cr.rowcount,
            table,
            old_column,
            table,
            new_column,
        )


# ============================================================
# Enterprise module uninstall
# ============================================================


def _mark_enterprise_modules_for_uninstall(env):
    """
    Mark Enterprise modules as 'to remove'.

    We intentionally use button_uninstall(), NOT
    button_immediate_uninstall(), because this code is running while
    Odoo is building/updating the registry.
    """

    modules = env["ir.module.module"].sudo().search(
        [
            ("name", "in", MODULES_TO_UNINSTALL),
            ("state", "in", ("installed", "to upgrade")),
        ]
    )

    if not modules:
        _logger.info(
            "No Enterprise modules from configured list need removal."
        )
        return

    _logger.info(
        "Marking Enterprise modules for uninstall: %s",
        modules.mapped("name"),
    )

    # DO NOT hide the exception.
    #
    # Uninstalling these modules is an important migration step.
    # If it fails, the installation should fail so that Odoo can
    # rollback the transaction correctly.
    modules.button_uninstall()


# ============================================================
# Community module installation
# ============================================================


def _mark_community_modules_for_install(env):
    """
    Mark Community replacement modules for installation.
    """

    modules = env["ir.module.module"].sudo().search(
        [
            ("name", "in", MODULES_TO_INSTALL),
            ("state", "=", "uninstalled"),
        ]
    )

    if not modules:
        _logger.info(
            "No configured Community modules need installation."
        )
        return

    _logger.info(
        "Marking Community modules for installation: %s",
        modules.mapped("name"),
    )

    # Same rule as uninstall:
    # do not swallow installation errors.
    modules.button_install()


# ============================================================
# Archive views
# ============================================================


def _archive_views(env):

    views = (
        env["ir.ui.view"]
        .sudo()
        .browse(VIEWS_TO_ARCHIVE)
        .exists()
    )

    if not views:
        _logger.info(
            "No configured views found to archive."
        )
        return

    views.write(
        {
            "active": False,
        }
    )

    _logger.info(
        "Archived views: %s",
        views.ids,
    )


# ============================================================
# Archive menus
# ============================================================


def _archive_menus(env):

    menus = (
        env["ir.ui.menu"]
        .sudo()
        .browse(MENUS_TO_ARCHIVE)
        .exists()
    )

    if not menus:
        _logger.info(
            "No configured menu items found to archive."
        )
        return

    menus.write(
        {
            "active": False,
        }
    )

    _logger.info(
        "Archived menu items: %s",
        menus.ids,
    )


# ============================================================
# Remove Enterprise view modes
# ============================================================


def _cleanup_enterprise_act_window_views(env):
    """
    Remove unsupported Enterprise-only view modes from
    ir.actions.act_window.

    Odoo Community 19 supports:
        list
        form
        graph
        pivot
        calendar
        kanban

    Enterprise-only values cleaned here:
        gantt
        grid
        cohort
        map
    """

    actions = (
        env["ir.actions.act_window"]
        .sudo()
        .search([])
    )

    changed = []

    for action_record in actions:

        old_view_mode = action_record.view_mode or ""

        modes = [
            mode.strip()
            for mode in old_view_mode.split(",")
            if mode.strip()
        ]

        new_modes = [
            mode
            for mode in modes
            if mode not in ENTERPRISE_VIEW_TYPES
        ]

        # If the action contained ONLY Enterprise modes,
        # give it a safe Community fallback.
        if modes and not new_modes:
            new_modes = FALLBACK_VIEW_MODE.split(",")

        new_view_mode = ",".join(new_modes)

        # ----------------------------------------------------
        # Main view_mode
        # ----------------------------------------------------

        if modes != new_modes:

            action_record.write(
                {
                    "view_mode": new_view_mode,
                }
            )

            changed.append(
                (
                    action_record.id,
                    action_record.name,
                    old_view_mode,
                    new_view_mode,
                )
            )

        # ----------------------------------------------------
        # Mobile view
        # ----------------------------------------------------

        if (
            action_record.mobile_view_mode
            in ENTERPRISE_VIEW_TYPES
        ):
            action_record.write(
                {
                    "mobile_view_mode": "kanban",
                }
            )

        # ----------------------------------------------------
        # Main specific view
        # ----------------------------------------------------

        if (
            action_record.view_id
            and action_record.view_id.type
            in ENTERPRISE_VIEW_TYPES
        ):
            action_record.write(
                {
                    "view_id": False,
                }
            )

        # ----------------------------------------------------
        # Action view lines
        # ----------------------------------------------------

        enterprise_lines = (
            action_record.view_ids.filtered(
                lambda line:
                line.view_mode
                in ENTERPRISE_VIEW_TYPES
            )
        )

        if enterprise_lines:
            enterprise_lines.unlink()

    if changed:

        _logger.info(
            "Enterprise view cleanup updated %s action(s).",
            len(changed),
        )

        for (
            action_id,
            name,
            old_mode,
            new_mode,
        ) in changed:

            _logger.info(
                "Action %s - %s: view_mode %s -> %s",
                action_id,
                name,
                old_mode,
                new_mode,
            )

    else:

        _logger.info(
            "Enterprise view cleanup: "
            "no action view_mode changes needed."
        )


# ============================================================
# Remove Studio field references from views
# ============================================================


def _strip_field_from_views(
    env,
    model_name,
    field_name,
):
    """
    Remove references to an old Studio field from views before
    deleting the ir.model.fields record.

    Odoo refuses to delete a manual field if a view still
    depends on that field.
    """

    views = (
        env["ir.ui.view"]
        .sudo()
        .with_context(active_test=False)
        .search(
            [
                ("model", "=", model_name),
                ("arch_db", "like", field_name),
            ]
        )
    )

    for view in views:

        # ----------------------------------------------------
        # Parse XML
        # ----------------------------------------------------

        try:

            arch = etree.fromstring(
                (view.arch_db or "").encode("utf-8")
            )

        except Exception as exc:

            _logger.warning(
                "Could not parse view %s (%s) "
                "while removing %s: %s",
                view.xml_id or view.id,
                view.name,
                field_name,
                exc,
            )

            continue

        changed = False

        # ----------------------------------------------------
        # Normal <field/>
        #
        # Example:
        # <field name="x_revenue"/>
        # ----------------------------------------------------

        for node in arch.xpath(
            f'.//field[@name="{field_name}"]'
        ):

            parent = node.getparent()

            if parent is not None:
                parent.remove(node)
                changed = True

        # ----------------------------------------------------
        # Search view filter/groupby
        # ----------------------------------------------------

        for tag in (
            "filter",
            "groupby",
        ):

            # Example:
            # <filter name="x_revenue"/>
            for node in arch.xpath(
                f'.//{tag}[@name="{field_name}"]'
            ):

                parent = node.getparent()

                if parent is not None:
                    parent.remove(node)
                    changed = True

            # ------------------------------------------------
            # context / domain references
            # ------------------------------------------------

            for attribute in (
                "context",
                "domain",
            ):

                xpath = (
                    f'.//{tag}'
                    f'[contains(@{attribute}, "{field_name}")]'
                )

                for node in arch.xpath(xpath):

                    parent = node.getparent()

                    if parent is not None:
                        parent.remove(node)
                        changed = True

        if not changed:
            continue

        new_arch = etree.tostring(
            arch,
            encoding="unicode",
        )

        # ----------------------------------------------------
        # IMPORTANT:
        #
        # view.write() can fail validation.
        #
        # Therefore it MUST run inside a PostgreSQL savepoint
        # if we intend to catch the exception and continue.
        # ----------------------------------------------------

        try:

            with env.cr.savepoint():

                view.write(
                    {
                        "arch_db": new_arch,
                    }
                )

            _logger.info(
                "Removed %s from view %s (%s)",
                field_name,
                view.xml_id or view.id,
                view.name,
            )

        except Exception:

            _logger.exception(
                "Could not update view %s (%s) "
                "while removing %s. "
                "The old field will be kept if Odoo "
                "cannot safely unlink it.",
                view.xml_id or view.id,
                view.name,
                field_name,
            )


# ============================================================
# Remove old Studio ir.model.fields
# ============================================================


def remove_ir_model_fields(env):
    """
    Safely remove old Studio fields after copying their data.

    IMPORTANT:

    Odoo's ir.model.fields.unlink() already handles dropping
    the database column for a manual stored field.

    Therefore there is NO raw ALTER TABLE fallback.
    """

    IrModelFields = (
        env["ir.model.fields"]
        .sudo()
    )

    for (
        table,
        old_field,
        _new_field,
    ) in FIELD_COPY_MAP:

        model_name = _table_to_model(table)

        field = IrModelFields.search(
            [
                ("model", "=", model_name),
                ("name", "=", old_field),
            ],
            limit=1,
        )

        if not field:

            _logger.info(
                "No ir.model.fields entry for %s.%s; "
                "nothing to remove.",
                model_name,
                old_field,
            )

            continue

        # ----------------------------------------------------
        # Only Studio/manual fields may be removed this way.
        # ----------------------------------------------------

        if field.state != "manual":

            _logger.warning(
                "Skipping removal of %s.%s because "
                "field state is %s, not manual.",
                model_name,
                old_field,
                field.state,
            )

            continue

        # ----------------------------------------------------
        # First clean view references.
        # ----------------------------------------------------

        _strip_field_from_views(
            env,
            model_name,
            old_field,
        )

        # ----------------------------------------------------
        # VERY IMPORTANT FIX
        #
        # field.unlink() can execute SQL and may fail.
        #
        # Because we want to log the error and continue,
        # it MUST be protected by savepoint().
        #
        # Otherwise PostgreSQL leaves the complete
        # transaction aborted and the next search() gives:
        #
        # InFailedSqlTransaction
        # ----------------------------------------------------

        try:

            with env.cr.savepoint():

                _logger.info(
                    "Unlinking old Studio field %s.%s",
                    model_name,
                    old_field,
                )

                field.unlink()

        except Exception:

            _logger.exception(
                "Could not safely unlink %s.%s. "
                "Keeping the old field and column.",
                model_name,
                old_field,
            )


# ============================================================
# POST INIT
# ============================================================


def post_init_hook(env):
    """
    One-time Enterprise -> Community migration cleanup.
    """

    _logger.info(
        "------------------------------Starting QZ migration post-init hook...-------------------------------"
    )

    # --------------------------------------------------------
    # STEP 1
    # Copy old Studio field data into new module fields.
    # --------------------------------------------------------

    _copy_field_values(env)

    # --------------------------------------------------------
    # STEP 2
    # Mark Enterprise modules for uninstall.
    # --------------------------------------------------------

    _mark_enterprise_modules_for_uninstall(env)

    # --------------------------------------------------------
    # STEP 3
    # Archive known problematic views.
    # --------------------------------------------------------

    _archive_views(env)

    # --------------------------------------------------------
    # STEP 4
    # Remove Enterprise-only action view modes.
    # --------------------------------------------------------

    _cleanup_enterprise_act_window_views(env)

    # --------------------------------------------------------
    # STEP 5
    # Install Community replacements.
    # --------------------------------------------------------

    _mark_community_modules_for_install(env)

    # --------------------------------------------------------
    # STEP 6
    # Remove old Studio fields.
    #
    # Successful ir.model.fields.unlink() automatically
    # removes its DB column.
    # --------------------------------------------------------

    remove_ir_model_fields(env)

    # --------------------------------------------------------
    # STEP 7
    # Archive menu items.
    # --------------------------------------------------------

    _archive_menus(env)

    # --------------------------------------------------------
    # DO NOT CALL cr.commit()
    #
    # Odoo's module loader owns this transaction.
    # --------------------------------------------------------

    _logger.info(
        "---------------------QZ migration post-init hook completed successfully."
    )