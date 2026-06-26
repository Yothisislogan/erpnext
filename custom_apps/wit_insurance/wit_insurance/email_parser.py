import re

import frappe

from wit_insurance.intake_review import create_intake_review
from wit_insurance.lead_intake import upsert_lead
from wit_insurance.settings import get_lead_mailbox, intake_review_required
from wit_insurance.vin import normalize_vin

EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE)
PHONE_RE = re.compile(r"(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}")
VIN_RE = re.compile(r"\b[A-HJ-NPR-Z0-9]{17}\b", re.IGNORECASE)
DATE_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b")
TAG_RE = re.compile(r"<[^>]+>")


def after_insert_communication(doc, method=None):
	if not _is_lead_mailbox_message(doc):
		return

	payload = parse_communication(doc)
	if not payload:
		return

	if intake_review_required():
		review = create_intake_review(payload, source="Email", source_communication=doc.name)
		_link_communication(doc, review.name, "WIT Intake Review")
		return

	lead = upsert_lead(payload, source="Email", source_communication=doc.name, bypass_review=True)
	_link_communication(doc, lead.name, "Lead")


def retry_unprocessed_lead_communications():
	communications = frappe.get_all(
		"Communication",
		filters={"creation": [">", frappe.utils.add_days(frappe.utils.nowdate(), -7)]},
		fields=["name"],
		limit=50,
		order_by="creation desc",
	)
	for row in communications:
		doc = frappe.get_doc("Communication", row.name)
		if _is_lead_mailbox_message(doc) and not getattr(doc, "reference_name", None):
			after_insert_communication(doc)


def parse_communication(doc):
	text = _communication_text(doc)
	if not text:
		return {}

	sender = getattr(doc, "sender", None) or getattr(doc, "email_from", None)
	email = _first_email(text) or _first_email(sender or "")
	phone = _first_phone(text)
	name = _label_value(text, ["name", "insured name", "customer name", "applicant name"])
	address = _label_value(text, ["address", "street address", "garaging address"])
	coverage_limits = _label_value(text, ["coverage limits", "limits", "requested limits"])
	next_action = _label_value(text, ["next action", "action item", "to do"])
	next_follow_up = _label_value(text, ["follow up", "next follow up", "call back"])
	conviction_date = _label_date(text, ["conviction date", "convicted", "violation date"])
	policy_type = _guess_policy_type(text, getattr(doc, "subject", ""))

	vehicles = [{"vin": normalize_vin(vin)} for vin in VIN_RE.findall(text)]
	drivers = _parse_driver_rows(text, name)
	incidents = []
	if conviction_date or re.search(r"\b(accident|violation|ticket|claim)\b", text, re.IGNORECASE):
		incidents.append(
			{
				"incident_type": "Violation" if conviction_date else "Other",
				"conviction_date": conviction_date,
				"description": _label_value(text, ["violation", "ticket", "accident", "claim"]) or "Imported from lead email",
			}
		)

	return {
		"name": name,
		"email": email,
		"phone": phone,
		"address": address,
		"policy_type": policy_type,
		"coverage_limits": coverage_limits,
		"drivers": drivers,
		"vehicles": vehicles,
		"incidents": incidents,
		"call_summary": text[:4000],
		"next_action": next_action,
		"next_follow_up": next_follow_up,
		"last_violation_conviction_date": conviction_date,
		"parse_confidence": "High" if email or phone else "Low",
	}


def _is_lead_mailbox_message(doc):
	lead_mailbox = get_lead_mailbox()
	fields = [
		getattr(doc, "recipients", ""),
		getattr(doc, "cc", ""),
		getattr(doc, "bcc", ""),
		getattr(doc, "email_account", ""),
		getattr(doc, "sender", ""),
		getattr(doc, "email_from", ""),
	]
	return lead_mailbox in " ".join(str(value or "").lower() for value in fields)


def _communication_text(doc):
	parts = [getattr(doc, "subject", ""), getattr(doc, "content", ""), getattr(doc, "text_content", "")]
	text = "\n".join(str(part or "") for part in parts if part)
	return _strip_html(text) if "<" in text and ">" in text else text


def _strip_html(text):
	text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
	text = re.sub(r"</p>|</div>|</li>", "\n", text, flags=re.IGNORECASE)
	return TAG_RE.sub(" ", text)


def _link_communication(doc, reference_name, reference_doctype):
	try:
		doc.db_set("reference_doctype", reference_doctype, update_modified=False)
		doc.db_set("reference_name", reference_name, update_modified=False)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "WIT lead communication link failed")


def _first_email(text):
	match = EMAIL_RE.search(str(text or ""))
	return match.group(0) if match else None


def _first_phone(text):
	match = PHONE_RE.search(str(text or ""))
	return match.group(0) if match else None


def _label_value(text, labels):
	for label in labels:
		match = re.search(rf"{re.escape(label)}\s*[:=-]\s*([^\n]+)", text, re.IGNORECASE)
		if match:
			return match.group(1).strip()
	return None


def _label_date(text, labels):
	value = _label_value(text, labels)
	if not value:
		return None
	match = DATE_RE.search(value)
	return match.group(1) if match else None


def _guess_policy_type(text, subject=""):
	haystack = f"{subject}\n{text}".lower()
	if "commercial auto" in haystack or "box truck" in haystack or "tow" in haystack:
		return "Commercial Auto"
	if "workers comp" in haystack or "workers compensation" in haystack:
		return "Workers Compensation"
	if "general liability" in haystack or "gl" in haystack:
		return "General Liability"
	if "renters" in haystack:
		return "Renters"
	if "home" in haystack or "homeowners" in haystack:
		return "Home"
	if "auto" in haystack or VIN_RE.search(haystack.upper()):
		return "Personal Auto"
	return "Unknown"


def _parse_driver_rows(text, fallback_name=None):
	drivers = []
	dob = _label_date(text, ["dob", "date of birth"])
	dl = _label_value(text, ["dl", "driver license", "drivers license", "license number"])
	if fallback_name or dob or dl:
		drivers.append(
			{
				"driver_name": fallback_name,
				"date_of_birth": dob,
				"driver_license_number": dl,
			}
		)
	return drivers
