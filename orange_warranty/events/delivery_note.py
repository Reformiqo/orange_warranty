def validate_foc(doc, method):
	"""Enforce zero rate on FOC Delivery Notes.

	Use `.get()` so a missing custom_is_foc field never raises, and zero the
	base_* fields too (plus a 100% discount) so ERPNext's downstream
	tax/GL totals stay consistent with the zeroed rate.
	"""
	if not doc.get("custom_is_foc"):
		return
	for item in doc.items:
		item.discount_percentage = 100
		item.rate = 0
		item.amount = 0
		item.base_rate = 0
		item.base_amount = 0
