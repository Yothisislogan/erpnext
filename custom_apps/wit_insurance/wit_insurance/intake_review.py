import json

import frappe

from wit_insurance.attachments import link_communication_files
from wit_insurance.matching import find_lead_candidates

MAX_STORED_PAYLOAD_CHARS = 200_000
MAX_LONG_TEXT_PREVIEW_CHARS = 4_000


def create_intake_review(payload: dict, source: str = "API", source_communication: str | None = None):
	payload = frappe._dict(payload or {})

	if source_communication:
		existing = frappe.db.get_value(
			"WIT Intake Review",
			{"source_communication": source_communication, "status": ["!=", "Rejected"]},
			"name",
		)
		if existing:
			return frappe.get_doc("WIT Intake Review", existing)

	candidates = find_lead_candidates(payload)
	review = frappe.new_doc("WIT Intake Review")
	review.status = "Pending Review"
	review.source = source
	review.source_communication = source_communication
	review.parse_confidence = payload.get("parse_confidence") or "Medium"
	review.candidate_matches = _safe_json(candidates)
	review.lead_name = payload.get("name") or payload.get("lead_name")
	review.email = payload.get("email") or payload.get("email_id")
	review.phone = payload.get("phone") or payload.get("mobile_no")
	review.full_address = payload.get("address") or payload.get("full_address")
	review.policy_type = payload.get("policy_type")
	review.coverage_limits = payload.get("coverage_limits")
	review.next_action = payload.get("next_action")
	review.next_follow_up = payload.get("next_follow_up")
	review.call_summary = payload.get("call_summary")
	review.parsed_payload = _safe_json(payload)
	review.missing_information = ", ".join(_missing_fields(payload))
	review.insert(ignore_permissions=True)
	return review


@frappe.whitelist(methods=["POST"])
def approve_intake_review(review_name: str):
	from wit_insurance.lead_intake import upsert_lead

	review = frappe.get_doc("WIT Intake Review", review_name)
	_assert_review_permission(review, require_lead_create=True)
	if review.status in {"Converted", "Approved"} and review.converted_lead:
		return {"lead": review.converted_lead, "status": review.status}

	payload = json.loads(review.parsed_payload or "{}")
	_apply_review_edits_to_payload(review, payload)
	lead = upsert_lead(payload, source=review.source or "Review", source_communication=review.source_communication, bypass_review=True)
	if review.source_communication:
		link_communication_files(review.source_communication, "Lead", lead.name)
	review.status = "Converted"
	review.converted_lead = lead.name
	review.save(ignore_permissions=False)
	return {"lead": lead.name, "review": review.name, "status": "Converted"}


@frappe.whitelist(methods=["POST"])
def reject_intake_review(review_name: str, reason: str | None = None):
	review = frappe.get_doc("WIT Intake Review", review_name)
	_assert_review_permission(review)
	review.status = "Rejected"
	if reason:
		review.review_notes = reason
	review.save(ignore_permissions=False)
	return {"review": review.name, "status": "Rejected"}


def _assert_review_permission(review, require_lead_create: bool = False):
	review.check_permission("write")
	if require_lead_create and not frappe.has_permission("Lead", "create"):
		frappe.throw("Not permitted to create Leads", frappe.PermissionError)


def _safe_json(value) -> str:
	content = json.dumps(value, indent=2, default=str)
	if len(content) <= MAX_STORED_PAYLOAD_CHARS:
		return content

	if isinstance(value, dict):
		compact = dict(value)
		for key in ("call_summary", "transcript", "raw_transcript", "content", "email_body"):
			if compact.get(key):
				compact[key] = str(compact[key])[:MAX_LONG_TEXT_PREVIEW_CHARS] + "\n... truncated for safety"
		compact["_truncated_for_safety"] = True
		return json.dumps(compact, indent=2, default=str)

	return json.dumps(
		{
			"_truncated_for_safety": True,
			"preview": content[:MAX_LONG_TEXT_PREVIEW_CHARS],
		},
		indent=2,
		default=str,
	)


def _apply_review_edits_to_payload(review, payload):
	mapping = {
		"name": "lead_name",
		"email": "email",
		"phone": "phone",
		"address": "full_address",
		"policy_type": "policy_type",
		"coverage_limits": "coverage_limits",
		"next_action": "next_action",
		"next_follow_up": "next_follow_up",
		"call_summary": "call_summary",
	}
	for payload_key, review_field in mapping.items():
		value = review.get(review_field)
		if value:
			payload[payload_key] = value


def _missing_fields(payload):
	missing = []
	if not (payload.get("name") or payload.get("lead_name")):
		missing.append("name")
	if not (payload.get("email") or payload.get("email_id")):
		missing.append("email")
	if not (payload.get("phone") or payload.get("mobile_no")):
		missing.append("phone")
	if not (payload.get("address") or payload.get("full_address")):
		missing.append("address")
	if not payload.get("policy_type"):
		missing.append("policy type")
	if not payload.get("coverage_limits"):
		missing.append("coverage limits")
	if not payload.get("drivers"):
		missing.append("drivers")
	if payload.get("policy_type") in {"Personal Auto", "Commercial Auto"} and not payload.get("vehicles"):
		missing.append("VIN / vehicles")
	if not payload.get("next_action"):
		missing.append("next action")
	return missing
