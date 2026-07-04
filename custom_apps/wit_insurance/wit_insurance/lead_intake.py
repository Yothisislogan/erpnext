import hmac
import json

import frappe
from frappe.utils import now_datetime

from wit_insurance.matching import find_lead_match
from wit_insurance.settings import default_lead_owner, intake_review_required, voip_api_token
from wit_insurance.vin import normalize_vin

MAX_VOIP_PAYLOAD_BYTES = 256 * 1024


@frappe.whitelist(methods=["POST"])
def upsert_lead_from_call(**kwargs):
	"""Create/update a Lead or create a review item from VOIP payload.

	Endpoint:
	/api/method/wit_insurance.lead_intake.upsert_lead_from_call
	"""
	_validate_voip_token()
	payload = _payload_from_request(kwargs)
	if intake_review_required():
		from wit_insurance.intake_review import create_intake_review

		review = create_intake_review(payload, source="VOIP")
		return {"review": review.name, "status": "Pending Review"}

	lead = upsert_lead(payload, source="VOIP", bypass_review=True)
	return {"lead": lead.name, "status": "updated"}


def upsert_lead(payload: dict, source: str = "API", source_communication: str | None = None, bypass_review: bool = False):
	payload = frappe._dict(payload or {})
	if not bypass_review and intake_review_required():
		from wit_insurance.intake_review import create_intake_review

		return create_intake_review(payload, source=source, source_communication=source_communication)

	lead = find_lead_match(payload)

	if not lead:
		lead = frappe.new_doc("Lead")
		lead.status = "Lead"
		if default_lead_owner():
			lead.lead_owner = default_lead_owner()

	_set_basic_fields(lead, payload)
	_set_insurance_fields(lead, payload, source_communication=source_communication)
	_merge_child_rows(lead, payload)

	if source_communication:
		lead.custom_source_communication = source_communication

	lead.custom_parse_confidence = payload.get("parse_confidence") or lead.custom_parse_confidence or "Medium"
	lead.save(ignore_permissions=True)

	if payload.get("call_summary") and source == "VOIP":
		_add_call_communication(lead, payload)

	return lead


def _payload_from_request(kwargs):
	if kwargs:
		return kwargs

	if frappe.request and frappe.request.data:
		if len(frappe.request.data) > MAX_VOIP_PAYLOAD_BYTES:
			frappe.throw("VOIP payload is too large", frappe.ValidationError)
		data = frappe.request.data.decode("utf-8")
		if data:
			payload = json.loads(data)
			if not isinstance(payload, dict):
				frappe.throw("VOIP payload must be a JSON object", frappe.ValidationError)
			return payload

	return frappe.form_dict or {}


def _validate_voip_token():
	expected = voip_api_token()
	if not expected:
		frappe.throw("VOIP API token is not configured", frappe.PermissionError)

	provided = None
	if frappe.request:
		provided = frappe.request.headers.get("X-WIT-VOIP-Token") or frappe.request.headers.get("Authorization")
	if provided and provided.startswith("Bearer "):
		provided = provided[7:]

	if not provided or not hmac.compare_digest(str(provided), str(expected)):
		frappe.throw("Invalid VOIP token", frappe.PermissionError)


def _set_basic_fields(lead, payload):
	full_name = payload.get("name") or payload.get("lead_name")
	if full_name and not (payload.get("first_name") or payload.get("last_name")):
		parts = str(full_name).strip().split()
		if parts:
			lead.first_name = lead.first_name or parts[0]
			lead.last_name = lead.last_name or " ".join(parts[1:])
		lead.lead_name = full_name

	for field, key in [
		("first_name", "first_name"),
		("last_name", "last_name"),
		("company_name", "company_name"),
		("email_id", "email"),
		("phone", "phone"),
		("mobile_no", "mobile_no"),
		("city", "city"),
		("state", "state"),
		("country", "country"),
	]:
		value = payload.get(key)
		if value and not lead.get(field):
			lead.set(field, value)

	if payload.get("address") or payload.get("full_address"):
		lead.custom_full_address = payload.get("address") or payload.get("full_address")


def _set_insurance_fields(lead, payload, source_communication=None):
	mapping = {
		"custom_policy_type": "policy_type",
		"custom_coverage_limits": "coverage_limits",
		"custom_next_action": "next_action",
		"custom_next_follow_up": "next_follow_up",
		"custom_call_summary": "call_summary",
		"custom_last_violation_conviction_date": "last_violation_conviction_date",
	}
	for field, key in mapping.items():
		value = payload.get(key)
		if value:
			lead.set(field, value)

	if source_communication:
		lead.custom_source_communication = source_communication


def _merge_child_rows(lead, payload):
	for driver in payload.get("drivers") or []:
		if not _driver_exists(lead, driver):
			lead.append("custom_wit_drivers", driver)

	existing_vins = {normalize_vin(row.vin) for row in lead.get("custom_wit_vehicles") or [] if row.vin}
	for vehicle in payload.get("vehicles") or []:
		vin = normalize_vin(vehicle.get("vin"))
		if vin and vin not in existing_vins:
			vehicle["vin"] = vin
			lead.append("custom_wit_vehicles", vehicle)
			existing_vins.add(vin)

	for incident in payload.get("incidents") or payload.get("accidents_violations") or []:
		lead.append("custom_accidents_violations", incident)
		if incident.get("conviction_date"):
			lead.custom_last_violation_conviction_date = incident.get("conviction_date")


def _driver_exists(lead, driver):
	name = (driver.get("driver_name") or driver.get("name") or "").strip().lower()
	dob = str(driver.get("date_of_birth") or driver.get("dob") or "")
	for row in lead.get("custom_wit_drivers") or []:
		if (row.driver_name or "").strip().lower() == name and str(row.date_of_birth or "") == dob:
			return True
	return False


def _add_call_communication(lead, payload):
	frappe.get_doc(
		{
			"doctype": "Communication",
			"communication_type": "Phone",
			"communication_medium": "Phone",
			"sent_or_received": "Received",
			"subject": payload.get("subject") or "WIT call summary",
			"content": payload.get("call_summary"),
			"reference_doctype": "Lead",
			"reference_name": lead.name,
			"communication_date": now_datetime(),
		}
	).insert(ignore_permissions=True)
