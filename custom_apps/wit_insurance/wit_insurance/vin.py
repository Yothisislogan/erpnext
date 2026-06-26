import json
import re
from urllib.parse import quote
from urllib.request import urlopen

import frappe

VIN_RE = re.compile(r"^[A-HJ-NPR-Z0-9]{17}$", re.IGNORECASE)


def normalize_vin(vin: str | None) -> str:
	return re.sub(r"[^A-HJ-NPR-Z0-9]", "", (vin or "").upper())


def is_valid_vin(vin: str | None) -> bool:
	return bool(VIN_RE.match(normalize_vin(vin)))


def decode_vin(vin: str | None) -> dict:
	"""Decode a VIN using the free NHTSA vPIC API.

	Returns a small normalized dict. The caller should keep the original VIN even
	when the remote lookup fails.
	"""
	clean_vin = normalize_vin(vin)
	if not is_valid_vin(clean_vin):
		return {"vin": clean_vin, "ok": False, "status": "Invalid VIN format"}

	url = f"https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVinValues/{quote(clean_vin)}?format=json"
	try:
		with urlopen(url, timeout=10) as response:
			payload = json.loads(response.read().decode("utf-8"))
	except Exception as exc:
		frappe.log_error(frappe.get_traceback(), "WIT VIN decode failed")
		return {"vin": clean_vin, "ok": False, "status": f"VIN lookup failed: {exc}"}

	results = payload.get("Results") or []
	if not results:
		return {"vin": clean_vin, "ok": False, "status": "No VIN decode result returned"}

	row = results[0]
	error_code = (row.get("ErrorCode") or "").strip()
	error_text = (row.get("ErrorText") or "").strip()
	ok = error_code in {"", "0"}

	return {
		"vin": clean_vin,
		"ok": ok,
		"year": row.get("ModelYear") or "",
		"make": row.get("Make") or "",
		"model": row.get("Model") or "",
		"body_class": row.get("BodyClass") or "",
		"vehicle_type": row.get("VehicleType") or "",
		"manufacturer": row.get("Manufacturer") or row.get("ManufacturerName") or "",
		"status": "Decoded" if ok else (error_text or f"VIN decode warning: {error_code}"),
	}
