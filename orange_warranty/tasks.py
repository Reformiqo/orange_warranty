import frappe
from frappe.utils import today


def daily_warranty_update():
	"""Flip Active to Expired for past-due warranties."""
	frappe.db.sql(
		"""
		UPDATE `tabWarranty Registration`
		SET warranty_status = 'Expired', remaining_warranty_days = 0
		WHERE warranty_status = 'Active'
		AND warranty_end_date < %s
	""",
		today(),
	)
	frappe.db.commit()  # nosemgrep
