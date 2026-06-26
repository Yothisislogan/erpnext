import re
from collections import defaultdict

import frappe
from frappe.utils import add_days, nowdate

from wit_insurance.settings import duplicate_match_days
from wit_insurance.vin import normalize_vin

PHONE_DIGITS_RE = re.compile(r"\D+")
AUTO_MATCH_MIN_SCORE = 70


def find_lead_match(payload: dict):
	candidates = find_lead_candidates(payload)
	if not candidates or candidates[0]["score"] < AUTO_MATCH_MIN_SCORE:
		return None
	return frappe.get_doc("Lead", candidates[0]["lead"])


def find_lead_candidates(payload: dict, limit: int = 5) -> list[dict]:
	payload = frappe._dict(payload or {})
	scores = defaultdict(lambda: {"score": 0, "reasons": set()})

	_email_match(payload, scores)
	_phone_match(payload, scores)
	_vin_match(payload, scores)
	_name_zip_match(payload, scores)

	rows = []
	for lead, info in scores.items():
		rows.append(
			{
				"lead": lead,
				"score": info["score"],
				"reasons": sorted(info["reasons"]),
				"auto_match": info["score"] >= AUTO_MATCH_MIN_SCORE,
			}
		)

	rows.sort(key=lambda row: row["score"], reverse=True)
	return rows[:limit]


def _email_match(payload, scores):
	email = payload.get("email") or payload.get("email_id")
	if not email:
		return
	for row in frappe.get_all("Lead", filters={"email_id": email}, fields=["name"], limit=10):
		_add_score(scores, row.name, 100, "email")


def _phone_match(payload, scores):
	phone = _digits(payload.get("phone") or payload.get("mobile_no"))
	if not phone:
		return

	since = add_days(nowdate(), -duplicate_match_days())
	for row in frappe.get_all(
		"Lead",
		filters={"modified": [">", since]},
		fields=["name", "phone", "mobile_no"],
		limit=250,
		order_by="modified desc",
	):
		if phone and phone in {_digits(row.phone), _digits(row.mobile_no)}:
			_add_score(scores, row.name, 80, "phone")


def _vin_match(payload, scores):
	vins = {normalize_vin(vehicle.get("vin")) for vehicle in payload.get("vehicles") or [] if vehicle.get("vin")}
	if not vins:
		return

	for vin in vins:
		for row in frappe.get_all(
			"WIT Vehicle",
			filters={"vin": vin},
			fields=["parent"],
			limit=20,
		):
			if row.parent:
				_add_score(scores, row.parent, 90, f"vin {vin}")


def _name_zip_match(payload, scores):
	name = (payload.get("name") or payload.get("lead_name") or "").strip().lower()
	zip_code = str(payload.get("zip") or payload.get("postal_code") or "").strip()
	if not name:
		return

	since = add_days(nowdate(), -duplicate_match_days())
	for row in frappe.get_all(
		"Lead",
		filters={"modified": [">", since]},
		fields=["name", "lead_name", "first_name", "last_name", "custom_full_address"],
		limit=250,
		order_by="modified desc",
	):
		lead_name = (row.lead_name or f"{row.first_name or ''} {row.last_name or ''}").strip().lower()
		if not lead_name:
			continue
		if lead_name == name:
			_add_score(scores, row.name, 45, "name")
			if zip_code and zip_code in str(row.custom_full_address or ""):
				_add_score(scores, row.name, 25, "zip")


def _add_score(scores, lead, points, reason):
	scores[lead]["score"] += points
	scores[lead]["reasons"].add(reason)


def _digits(value):
	return PHONE_DIGITS_RE.sub("", str(value or ""))
