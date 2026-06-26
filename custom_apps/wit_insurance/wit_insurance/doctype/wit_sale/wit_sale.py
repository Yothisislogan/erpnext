import frappe
from frappe.model.document import Document
from frappe.utils import nowdate


class WITSale(Document):
	def validate(self):
		if not self.sales_date:
			self.sales_date = nowdate()
		if not self.producer:
			self.producer = frappe.session.user
		if not self.producer_name and self.producer:
			self.producer_name = frappe.db.get_value("User", self.producer, "full_name") or self.producer
		self.commission = calculate_commission(self.premium, self.commission_rate)


def calculate_commission(premium, commission_rate):
	try:
		return round(float(premium or 0) * float(commission_rate or 0) / 100, 2)
	except (TypeError, ValueError):
		return 0
