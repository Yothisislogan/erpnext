import frappe
from frappe.utils import flt, getdate, nowdate

from wit_insurance.settings import (
	agency_monthly_commission_goal,
	agency_monthly_policy_goal,
	agency_monthly_premium_goal,
)

SALE_FIELDS = [
	"name",
	"sales_date",
	"producer",
	"producer_name",
	"customer",
	"lead",
	"line",
	"carrier",
	"business_type",
	"status",
	"premium",
	"commission_rate",
	"commission",
	"notes",
]


@frappe.whitelist()
def summary(scope="agency", period="MTD", from_date=None, to_date=None):
	start, end = _period_bounds(period, from_date, to_date)
	conditions, values = _base_conditions(scope, start, end)

	bound = frappe.db.sql(
		f"""
		SELECT COALESCE(SUM(premium), 0) AS premium,
		       COALESCE(SUM(commission), 0) AS commission,
		       COUNT(*) AS policies
		FROM `tabWIT Sale`
		WHERE status='Bound' {conditions}
		""",
		values,
		as_dict=True,
	)[0]

	today = nowdate()
	today_values = dict(values)
	today_values["today"] = today
	today_row = frappe.db.sql(
		f"""
		SELECT COALESCE(SUM(premium), 0) AS premium, COUNT(*) AS policies
		FROM `tabWIT Sale`
		WHERE status='Bound' {conditions} AND sales_date=%(today)s
		""",
		today_values,
		as_dict=True,
	)[0]

	pending = frappe.db.sql(
		f"""
		SELECT COALESCE(SUM(premium), 0) AS premium, COUNT(*) AS policies
		FROM `tabWIT Sale`
		WHERE status in ('Quoted', 'Pending') {conditions}
		""",
		values,
		as_dict=True,
	)[0]

	goals = _goals_for_scope(scope, start)
	premium = flt(bound.premium)
	commission = flt(bound.commission)
	policies = int(bound.policies or 0)

	return {
		"scope": scope,
		"period": period,
		"from_date": start,
		"to_date": end,
		"mtdPremium": premium,
		"mtdCommission": commission,
		"mtdPolicies": policies,
		"todayPremium": flt(today_row.premium),
		"todayPolicies": int(today_row.policies or 0),
		"pendingPremium": flt(pending.premium),
		"pendingPolicies": int(pending.policies or 0),
		"goals": goals,
		"goalProgress": {
			"premium": _pct(premium, goals.get("premium_goal")),
			"policies": _pct(policies, goals.get("policy_goal")),
			"commission": _pct(commission, goals.get("commission_goal")),
		},
	}


@frappe.whitelist()
def leaderboard(metric="premium", scope="agency", period="MTD", from_date=None, to_date=None, business_type=None, carrier=None):
	start, end = _period_bounds(period, from_date, to_date)
	conditions, values = _base_conditions(scope, start, end)
	if business_type:
		conditions += " AND business_type=%(business_type)s"
		values["business_type"] = business_type
	if carrier:
		conditions += " AND carrier=%(carrier)s"
		values["carrier"] = carrier

	agg = {
		"premium": "COALESCE(SUM(premium), 0)",
		"policies": "COUNT(*)",
		"commission": "COALESCE(SUM(commission), 0)",
	}.get(metric, "COALESCE(SUM(premium), 0)")

	rows = frappe.db.sql(
		f"""
		SELECT COALESCE(NULLIF(producer_name, ''), producer, 'Unassigned') AS producer,
		       {agg} AS value
		FROM `tabWIT Sale`
		WHERE status='Bound' {conditions}
		GROUP BY COALESCE(NULLIF(producer_name, ''), producer, 'Unassigned')
		ORDER BY value DESC
		""",
		values,
		as_dict=True,
	)
	return {"metric": metric, "rows": rows}


@frappe.whitelist()
def list_sales(scope="agency", period="MTD", from_date=None, to_date=None, status=None, search=None):
	start, end = _period_bounds(period, from_date, to_date)
	filters = {"sales_date": ["between", [start, end]]}
	if status:
		filters["status"] = status
	if scope == "mine":
		filters["producer"] = frappe.session.user

	rows = frappe.get_all(
		"WIT Sale",
		filters=filters,
		fields=SALE_FIELDS,
		order_by="sales_date desc, modified desc",
		limit=200,
	)
	if search:
		needle = str(search).lower()
		rows = [row for row in rows if needle in " ".join(str(v or "") for v in row.values()).lower()]
	return rows


@frappe.whitelist(methods=["POST"])
def create_sale(**kwargs):
	payload = _payload(kwargs)
	sale = frappe.new_doc("WIT Sale")
	_set_sale_fields(sale, payload)
	sale.insert(ignore_permissions=False)
	return sale.as_dict()


@frappe.whitelist(methods=["POST"])
def update_sale(name, **kwargs):
	payload = _payload(kwargs)
	sale = frappe.get_doc("WIT Sale", name)
	_set_sale_fields(sale, payload)
	sale.save(ignore_permissions=False)
	return sale.as_dict()


def _set_sale_fields(sale, payload):
	for field in [
		"sales_date",
		"producer",
		"producer_name",
		"customer",
		"lead",
		"line",
		"carrier",
		"business_type",
		"status",
		"premium",
		"commission_rate",
		"notes",
	]:
		if field in payload:
			sale.set(field, payload.get(field))
	if not sale.producer:
		sale.producer = frappe.session.user


def _payload(kwargs):
	if kwargs:
		return frappe._dict(kwargs)
	if frappe.request and frappe.request.json:
		return frappe._dict(frappe.request.json)
	return frappe._dict(frappe.form_dict or {})


def _period_bounds(period, from_date=None, to_date=None):
	today = getdate(nowdate())
	period = period or "MTD"
	if period == "YTD":
		return f"{today.year}-01-01", today.isoformat()
	if period == "ALL":
		return "0001-01-01", "9999-12-31"
	if period == "CUSTOM" and from_date and to_date:
		return getdate(from_date).isoformat(), getdate(to_date).isoformat()
	return today.replace(day=1).isoformat(), today.isoformat()


def _base_conditions(scope, start, end):
	conditions = " AND sales_date >= %(start)s AND sales_date <= %(end)s"
	values = {"start": start, "end": end}
	if scope == "mine":
		conditions += " AND producer=%(producer)s"
		values["producer"] = frappe.session.user
	return conditions, values


def _goals_for_scope(scope, start):
	if scope == "mine":
		goal_month = str(start)[:7]
		row = frappe.get_all(
			"WIT Producer Goal",
			filters={"producer": frappe.session.user, "goal_month": goal_month},
			fields=["premium_goal", "policy_goal", "commission_goal"],
			limit=1,
		)
		if row:
			return row[0]
	return {
		"premium_goal": agency_monthly_premium_goal(),
		"policy_goal": agency_monthly_policy_goal(),
		"commission_goal": agency_monthly_commission_goal(),
	}


def _pct(value, goal):
	goal = flt(goal)
	if not goal:
		return 0
	return min(999, round((flt(value) / goal) * 100, 1))
