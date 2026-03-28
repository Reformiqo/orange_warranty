import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import date_diff, getdate, today


class WarrantyRegistration(Document):
	def validate(self):
		self.validate_dates()
		self.compute_warranty_status()
		self.sync_serial_no()

	def validate_dates(self):
		if self.warranty_start_date and self.warranty_end_date:
			if getdate(self.warranty_end_date) < getdate(self.warranty_start_date):
				frappe.throw(_("Warranty End Date cannot be before Start Date."))

	def compute_warranty_status(self):
		if self.warranty_end_date:
			remaining = date_diff(self.warranty_end_date, today())
			self.remaining_warranty_days = max(remaining, 0)
			self.warranty_status = "Active" if remaining > 0 else "Expired"

	def sync_serial_no(self):
		if self.serial_number and frappe.db.exists("Serial No", self.serial_number):
			frappe.db.set_value(
				"Serial No",
				self.serial_number,
				{
					"warranty_expiry_date": self.warranty_end_date,
					"custom_warranty_type": self.warranty_type,
					"custom_warranty_registration": self.name,
				},
			)
