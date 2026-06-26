import frappe

from wit_insurance.custom_fields import sync_custom_fields


def after_install():
	sync_custom_fields()
	seed_settings()


def after_migrate():
	sync_custom_fields()
	seed_settings()


def seed_settings():
	if not frappe.db.exists("DocType", "WIT Insurance Settings"):
		return

	settings = frappe.get_single("WIT Insurance Settings")
	if not settings.lead_mailbox:
		settings.lead_mailbox = "leads@weinsurethings.com"
	if not settings.follow_up_months:
		settings.follow_up_months = 35
	if not settings.duplicate_match_days:
		settings.duplicate_match_days = 365
	settings.enable_vin_decode = 1 if settings.enable_vin_decode is None else settings.enable_vin_decode
	settings.require_intake_review = 1 if settings.require_intake_review is None else settings.require_intake_review
	settings.save(ignore_permissions=True)
