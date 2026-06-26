app_name = "wit_insurance"
app_title = "We Insure Things"
app_publisher = "We Insure Things"
app_description = "WIT branded insurance CRM workflows for ERPNext"
app_icon = "octicon octicon-shield"
app_color = "#00AEEF"
app_email = "logan@weinsurethings.com"
app_license = "MIT"

required_apps = ["frappe", "erpnext"]

app_include_css = ["/assets/wit_insurance/css/wit_brand.css"]
web_include_css = ["/assets/wit_insurance/css/wit_brand.css"]

after_install = "wit_insurance.install.after_install"
after_migrate = "wit_insurance.install.after_migrate"

doctype_js = {
	"Lead": "public/js/lead.js",
	"WIT Intake Review": "public/js/wit_intake_review.js",
}

doc_events = {
	"Lead": {
		"validate": "wit_insurance.lead_hooks.validate_lead",
		"on_update": "wit_insurance.lead_hooks.on_update_lead",
	},
	"Communication": {
		"after_insert": "wit_insurance.email_parser.after_insert_communication",
	},
}

scheduler_events = {
	"hourly": [
		"wit_insurance.email_parser.retry_unprocessed_lead_communications",
	]
}
