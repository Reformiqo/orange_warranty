def validate_foc(doc, method):
	"""Enforce zero rate on FOC Delivery Notes."""
	if not doc.custom_is_foc:
		return
	for item in doc.items:
		if item.rate != 0:
			item.rate = 0
		if item.amount != 0:
			item.amount = 0
