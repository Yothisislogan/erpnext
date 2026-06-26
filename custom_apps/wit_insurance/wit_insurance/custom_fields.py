import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def sync_custom_fields():
	"""Create/update WIT insurance CRM fields on ERPNext Lead."""
	custom_fields = {
		"Lead": [
			{
				"fieldname": "custom_wit_insurance_tab",
				"label": "Insurance Intake",
				"fieldtype": "Tab Break",
				"insert_after": "contact_info_tab",
			},
			{
				"fieldname": "custom_policy_type",
				"label": "Policy Type",
				"fieldtype": "Select",
				"options": "\nPersonal Auto\nHome\nRenters\nCommercial Auto\nGeneral Liability\nWorkers Compensation\nBOP\nSpecialty\nUnknown",
				"insert_after": "custom_wit_insurance_tab",
				"in_list_view": 1,
				"in_standard_filter": 1,
			},
			{
				"fieldname": "custom_coverage_limits",
				"label": "Coverage Limits",
				"fieldtype": "Small Text",
				"insert_after": "custom_policy_type",
			},
			{
				"fieldname": "custom_next_action",
				"label": "Next Action",
				"fieldtype": "Small Text",
				"insert_after": "custom_coverage_limits",
			},
			{
				"fieldname": "custom_next_follow_up",
				"label": "Next Follow-Up",
				"fieldtype": "Datetime",
				"insert_after": "custom_next_action",
			},
			{
				"fieldname": "custom_call_summary",
				"label": "Call Summary",
				"fieldtype": "Long Text",
				"insert_after": "custom_next_follow_up",
			},
			{
				"fieldname": "custom_missing_information",
				"label": "Missing Information",
				"fieldtype": "Small Text",
				"read_only": 1,
				"insert_after": "custom_call_summary",
			},
			{
				"fieldname": "custom_driver_vehicle_section",
				"label": "Drivers and Vehicles",
				"fieldtype": "Section Break",
				"insert_after": "custom_missing_information",
			},
			{
				"fieldname": "custom_wit_drivers",
				"label": "Drivers",
				"fieldtype": "Table",
				"options": "WIT Driver",
				"insert_after": "custom_driver_vehicle_section",
			},
			{
				"fieldname": "custom_wit_vehicles",
				"label": "Vehicles / VINs",
				"fieldtype": "Table",
				"options": "WIT Vehicle",
				"insert_after": "custom_wit_drivers",
			},
			{
				"fieldname": "custom_incident_section",
				"label": "Accidents and Violations",
				"fieldtype": "Section Break",
				"insert_after": "custom_wit_vehicles",
			},
			{
				"fieldname": "custom_accidents_violations",
				"label": "Accidents / Violations",
				"fieldtype": "Table",
				"options": "WIT Incident",
				"insert_after": "custom_incident_section",
			},
			{
				"fieldname": "custom_follow_up_rules_section",
				"label": "Follow-Up Rules",
				"fieldtype": "Section Break",
				"insert_after": "custom_accidents_violations",
			},
			{
				"fieldname": "custom_last_violation_conviction_date",
				"label": "Last Violation Conviction Date",
				"fieldtype": "Date",
				"insert_after": "custom_follow_up_rules_section",
			},
			{
				"fieldname": "custom_violation_follow_up_date",
				"label": "Violation Follow-Up Date",
				"fieldtype": "Date",
				"read_only": 1,
				"insert_after": "custom_last_violation_conviction_date",
			},
			{
				"fieldname": "custom_auto_followup_required",
				"label": "Auto Follow-Up Required",
				"fieldtype": "Check",
				"insert_after": "custom_violation_follow_up_date",
			},
			{
				"fieldname": "custom_vin_decode_status",
				"label": "VIN Decode Status",
				"fieldtype": "Small Text",
				"read_only": 1,
				"insert_after": "custom_auto_followup_required",
			},
			{
				"fieldname": "custom_source_communication",
				"label": "Source Communication",
				"fieldtype": "Link",
				"options": "Communication",
				"insert_after": "custom_vin_decode_status",
			},
			{
				"fieldname": "custom_parse_confidence",
				"label": "Parse Confidence",
				"fieldtype": "Select",
				"options": "\nHigh\nMedium\nLow",
				"insert_after": "custom_source_communication",
			},
		]
	}

	create_custom_fields(custom_fields, update=True)
	frappe.clear_cache(doctype="Lead")
