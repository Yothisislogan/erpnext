import re

import frappe
from frappe.utils import add_months, getdate

from wit_insurance.vin import decode_vin, normalize_vin

DATE_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b")
VIN_RE = re.compile(r"\b[A-HJ-NPR-Z0-9]{17}\b", re.IGNORECASE)
PHONE_RE = re.compile(r"(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}")
EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE)


def validate_lead(doc, method=None):
	_fill_from_summary(doc)
	_decode_vehicle_rows(doc)
	_apply_violation_follow_up_rule(doc)
	doc.custom_missing_information = ", ".join(_missing_fields(doc))


def on_update_lead(doc, method=None):
	_create_next_action_todo(doc)
	_create_violation_follow_up_todo(doc)


def _fill_from_summary(doc):
	text = _summary_text(doc)
	if not text:
		return

	if not doc.email_id:
		match = EMAIL_RE.search(text)
		if match:
			doc.email_id = match.group(0)

	if not doc.phone and not doc.mobile_no:
		match = PHONE_RE.search(text)
		if match:
			doc.phone = match.group(0)

	if not doc.custom_coverage_limits:
		match = re.search(r"(?:limits?|coverage limits?)\s*[:=-]\s*([^\n.;]+)", text, re.IGNORECASE)
		if match:
			doc.custom_coverage_limits = match.group(1).strip()

	if not doc.custom_next_action:
		match = re.search(r"(?:next action|action item|to do)\s*[:=-]\s*([^\n.;]+)", text, re.IGNORECASE)
		if match:
			doc.custom_next_action = match.group(1).strip()

	if not doc.custom_last_violation_conviction_date:
		match = re.search(r"(?:conviction date|convicted|violation date)\s*[:=-]\s*([^\n.;]+)", text, re.IGNORECASE)
		if match:
			doc.custom_last_violation_conviction_date = _coerce_date(match.group(1))

	_existing_vins = {normalize_vin(row.vin) for row in doc.get("custom_wit_vehicles") or [] if row.vin}
	for vin in VIN_RE.findall(text):
		clean_vin = normalize_vin(vin)
		if clean_vin and clean_vin not in _existing_vins:
			doc.append("custom_wit_vehicles", {"vin": clean_vin})
			_existing_vins.add(clean_vin)


def _decode_vehicle_rows(doc):
	statuses = []
	for row in doc.get("custom_wit_vehicles") or []:
		clean_vin = normalize_vin(row.vin)
		if not clean_vin:
			continue
		row.vin = clean_vin
		if row.make and row.model and row.year:
			continue

		decoded = decode_vin(clean_vin)
		row.year = decoded.get("year") or row.year
		row.make = decoded.get("make") or row.make
		row.model = decoded.get("model") or row.model
		row.body_class = decoded.get("body_class") or row.body_class
		row.vehicle_type = decoded.get("vehicle_type") or row.vehicle_type
		row.manufacturer = decoded.get("manufacturer") or row.manufacturer
		row.decode_status = decoded.get("status") or row.decode_status
		statuses.append(f"{clean_vin}: {row.decode_status or 'Checked'}")

	if statuses:
		doc.custom_vin_decode_status = "\n".join(statuses[:10])


def _apply_violation_follow_up_rule(doc):
	conviction_date = doc.custom_last_violation_conviction_date
	for row in doc.get("custom_accidents_violations") or []:
		if row.conviction_date:
			if not conviction_date or getdate(row.conviction_date) > getdate(conviction_date):
				conviction_date = row.conviction_date

	if not conviction_date:
		return

	doc.custom_last_violation_conviction_date = conviction_date
	follow_up = add_months(getdate(conviction_date), 35)
	doc.custom_violation_follow_up_date = follow_up
	doc.custom_auto_followup_required = 1

	for row in doc.get("custom_accidents_violations") or []:
		if row.conviction_date and not row.follow_up_date:
			row.follow_up_date = add_months(getdate(row.conviction_date), 35)


def _create_next_action_todo(doc):
	if not doc.custom_next_action or not doc.custom_next_follow_up:
		return
	_create_unique_todo(
		doc,
		description=f"Next action: {doc.custom_next_action}",
		date=doc.custom_next_follow_up,
	)


def _create_violation_follow_up_todo(doc):
	if not doc.custom_auto_followup_required or not doc.custom_violation_follow_up_date:
		return
	_create_unique_todo(
		doc,
		description="Re-shop / follow up because violation is aging off",
		date=doc.custom_violation_follow_up_date,
	)


def _create_unique_todo(doc, description, date):
	filters = {
		"reference_type": "Lead",
		"reference_name": doc.name,
		"description": description,
		"date": getdate(date),
		"status": ["!=", "Cancelled"],
	}
	if frappe.db.exists("ToDo", filters):
		return

	frappe.get_doc(
		{
			"doctype": "ToDo",
			"allocated_to": doc.lead_owner or frappe.session.user,
			"reference_type": "Lead",
			"reference_name": doc.name,
			"description": description,
			"date": getdate(date),
			"status": "Open",
			"priority": "Medium",
		}
	).insert(ignore_permissions=True)


def _missing_fields(doc):
	missing = []
	if not (doc.first_name or doc.lead_name or doc.company_name):
		missing.append("name")
	if not doc.email_id:
		missing.append("email")
	if not (doc.mobile_no or doc.phone):
		missing.append("phone")
	if not doc.custom_policy_type:
		missing.append("policy type")
	if not doc.custom_coverage_limits:
		missing.append("coverage limits")
	if not doc.get("custom_wit_drivers"):
		missing.append("drivers")
	if doc.custom_policy_type in {"Personal Auto", "Commercial Auto"} and not doc.get("custom_wit_vehicles"):
		missing.append("VIN / vehicles")
	if not doc.custom_next_action:
		missing.append("next action")
	return missing


def _summary_text(doc):
	return "\n".join(
		str(value or "")
		for value in [doc.custom_call_summary, getattr(doc, "notes", None)]
		if value
	)


def _coerce_date(value):
	match = DATE_RE.search(str(value or ""))
	if not match:
		return None
	try:
		return getdate(match.group(1))
	except Exception:
		return None
