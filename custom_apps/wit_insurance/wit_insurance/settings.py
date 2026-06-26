import frappe

DEFAULT_LEAD_MAILBOX = "leads@weinsurethings.com"
DEFAULT_FOLLOW_UP_MONTHS = 35
DEFAULT_DUPLICATE_MATCH_DAYS = 365


def get_settings():
	try:
		return frappe.get_single("WIT Insurance Settings")
	except Exception:
		return frappe._dict(
			{
				"lead_mailbox": DEFAULT_LEAD_MAILBOX,
				"enable_vin_decode": 1,
				"require_intake_review": 1,
				"follow_up_months": DEFAULT_FOLLOW_UP_MONTHS,
				"duplicate_match_days": DEFAULT_DUPLICATE_MATCH_DAYS,
				"enable_email_notifications": 1,
			}
		)


def get_lead_mailbox() -> str:
	return (get_settings().get("lead_mailbox") or DEFAULT_LEAD_MAILBOX).lower().strip()


def vin_decode_enabled() -> bool:
	return bool(get_settings().get("enable_vin_decode"))


def intake_review_required() -> bool:
	return bool(get_settings().get("require_intake_review"))


def follow_up_months() -> int:
	try:
		return int(get_settings().get("follow_up_months") or DEFAULT_FOLLOW_UP_MONTHS)
	except Exception:
		return DEFAULT_FOLLOW_UP_MONTHS


def duplicate_match_days() -> int:
	try:
		return int(get_settings().get("duplicate_match_days") or DEFAULT_DUPLICATE_MATCH_DAYS)
	except Exception:
		return DEFAULT_DUPLICATE_MATCH_DAYS


def default_lead_owner():
	return get_settings().get("default_lead_owner")


def default_followup_owner():
	return get_settings().get("default_followup_owner") or default_lead_owner()


def voip_api_token():
	settings = get_settings()
	try:
		return settings.get_password("voip_api_token")
	except Exception:
		return settings.get("voip_api_token")


def email_notifications_enabled() -> bool:
	return bool(get_settings().get("enable_email_notifications"))


def notification_recipients() -> list[str]:
	settings = get_settings()
	raw = settings.get("notification_recipients") or settings.get("default_followup_owner") or settings.get("default_lead_owner") or ""
	if isinstance(raw, list):
		return [item for item in raw if item]
	return [part.strip() for part in str(raw).replace(";", ",").split(",") if part.strip()]


def agency_monthly_premium_goal() -> float:
	return float(get_settings().get("agency_monthly_premium_goal") or 0)


def agency_monthly_policy_goal() -> int:
	return int(get_settings().get("agency_monthly_policy_goal") or 0)


def agency_monthly_commission_goal() -> float:
	return float(get_settings().get("agency_monthly_commission_goal") or 0)
