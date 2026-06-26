import frappe
from frappe.utils import fmt_money, get_url_to_form

from wit_insurance.settings import email_notifications_enabled, get_settings, notification_recipients


def intake_review_created(doc, method=None):
	settings = get_settings()
	if not settings.get("notify_on_intake_review"):
		return
	_send_wit_email(
		subject=f"New WIT intake review: {doc.lead_name or doc.email or doc.phone or doc.name}",
		title="New intake review",
		message=f"A new lead intake review is waiting for approval: {doc.name}",
		doc=doc,
	)


def sale_logged(doc, method=None):
	settings = get_settings()
	if not settings.get("notify_on_sale_logged") or doc.status != "Bound":
		return
	premium = fmt_money(doc.premium or 0)
	commission = fmt_money(doc.commission or 0)
	_send_wit_email(
		subject=f"New WIT sale logged: {doc.customer}",
		title="New sale logged",
		message=f"{doc.customer} was logged as Bound. Premium: {premium}. Commission: {commission}.",
		doc=doc,
	)


def quote_status_changed(doc, method=None):
	previous = doc.get_doc_before_save()
	if not previous or previous.status == doc.status:
		return

	settings = get_settings()
	if doc.status == "Lost" and settings.get("notify_on_quote_lost"):
		_send_wit_email(
			subject=f"WIT quote lost: {doc.customer}",
			title="Quote marked lost",
			message=f"Quote {doc.name} for {doc.customer} was marked Lost. Reason: {doc.lost_reason or 'Not provided'}.",
			doc=doc,
		)
	elif doc.status == "Sold" and settings.get("notify_on_quote_sold"):
		_send_wit_email(
			subject=f"WIT quote sold: {doc.customer}",
			title="Quote marked sold",
			message=f"Quote {doc.name} for {doc.customer} was marked Sold.",
			doc=doc,
		)


def _send_wit_email(subject: str, title: str, message: str, doc):
	if not email_notifications_enabled():
		return
	recipients = notification_recipients()
	if not recipients:
		return

	link = get_url_to_form(doc.doctype, doc.name)
	html = f"""
	<div style="font-family:Arial,sans-serif;background:#f4f8fb;padding:24px">
	  <div style="max-width:620px;margin:auto;background:#fff;border:1px solid #dbe7f1;border-radius:14px;overflow:hidden">
	    <div style="background:#06121D;color:#fff;padding:18px 22px">
	      <strong style="font-size:18px">We Insure Things</strong>
	    </div>
	    <div style="padding:22px">
	      <h2 style="margin:0 0 10px;color:#06121D">{frappe.utils.escape_html(title)}</h2>
	      <p style="color:#36485a;font-size:15px;line-height:1.5">{frappe.utils.escape_html(message)}</p>
	      <p><a href="{link}" style="background:#00AEEF;color:#fff;padding:10px 14px;border-radius:8px;text-decoration:none;font-weight:bold">Open in ERPNext</a></p>
	    </div>
	  </div>
	</div>
	"""
	frappe.sendmail(recipients=recipients, subject=subject, message=html, delayed=True)
