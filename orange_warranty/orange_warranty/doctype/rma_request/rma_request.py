import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, getdate, nowdate, today


class RMARequest(Document):
	def validate(self):
		self.check_warranty()
		self.check_duplicate()
		self.validate_replacement_cost()

	def check_warranty(self):
		"""Auto-set warranty flags based on end date."""
		if self.warranty_end_date and getdate(self.warranty_end_date) >= getdate(today()):
			self.is_under_warranty = 1
			self.is_foc = 1
			self.replacement_cost = 0
			self.director_approval_required = 0
			self.director_approval_status = "Not Required"
		else:
			self.is_under_warranty = 0
			self.is_foc = 0
			self.director_approval_required = 1
			if not self.director_approval_status or self.director_approval_status == "Not Required":
				self.director_approval_status = "Pending"

	def check_duplicate(self):
		"""Prevent duplicate active RMA for same serial."""
		if not self.serial_number:
			return
		existing = frappe.db.exists(
			"RMA Request",
			{
				"serial_number": self.serial_number,
				"rma_status": ["not in", ["Rejected", "Closed"]],
				"name": ["!=", self.name or ""],
				"docstatus": ["!=", 2],
			},
		)
		if existing:
			frappe.throw(
				_("Active RMA {0} already exists for serial {1}").format(existing, self.serial_number),
				title=_("Duplicate RMA"),
			)

	def validate_replacement_cost(self):
		"""Ensure non-negative replacement cost."""
		if flt(self.replacement_cost) < 0:
			frappe.throw(_("Replacement Cost cannot be negative."))

	def before_submit(self):
		"""Guard: block submit if director approval pending."""
		if self.director_approval_required and self.director_approval_status != "Approved":
			frappe.throw(
				_("Director approval is required for non-warranty RMA."),
				title=_("Approval Required"),
			)
		if self.serial_number:
			self.old_serial_number = self.serial_number

	def on_update_after_submit(self):
		"""Post-submit automation triggers."""
		# 1. Create FOC DN when replacement serial is set (first time only)
		if self.is_foc and self.new_serial_number and not self.foc_delivery_note:
			self.create_foc_delivery_note()

		# 2. Create inward SE when faulty part received
		if self.faulty_part_received and not self.inward_stock_entry:
			self.create_inward_stock_entry()

		# 3. Swap serial when RMA is closed
		if self.rma_status == "Closed" and self.new_serial_number:
			self.update_warranty_registration()

	def on_cancel(self):
		"""Cancel linked auto-created documents."""
		for field, doctype in [
			("foc_delivery_note", "Delivery Note"),
			("inward_stock_entry", "Stock Entry"),
		]:
			linked_name = self.get(field)
			if linked_name and frappe.db.exists(doctype, linked_name):
				linked_doc = frappe.get_doc(doctype, linked_name)
				if linked_doc.docstatus == 1:
					linked_doc.cancel()
				self.db_set(field, "")

	def create_foc_delivery_note(self):
		"""Auto-create zero-rate DN with replacement serial."""
		dn = frappe.new_doc("Delivery Note")
		dn.customer = self.customer
		dn.custom_is_foc = 1
		dn.custom_rma_reference = self.name
		dn.custom_warranty_type = self.warranty_type

		item_row = {
			"item_code": self.item_code,
			"qty": 1,
			"rate": 0,
			"warehouse": self.warehouse,
		}
		if self.new_serial_number:
			item_row["serial_no"] = self.new_serial_number

		dn.append("items", item_row)
		dn.flags.ignore_permissions = True
		dn.insert()
		dn.submit()

		self.db_set("foc_delivery_note", dn.name)
		self.db_set("date_of_dispatch", nowdate())

	def create_inward_stock_entry(self):
		"""Auto-create Material Receipt for faulty item."""
		se = frappe.new_doc("Stock Entry")
		se.stock_entry_type = "Material Receipt"
		se.custom_rma_reference = self.name
		se.custom_rma_purpose = "Faulty Inward"

		item_row = {
			"item_code": self.item_code,
			"qty": 1,
			"t_warehouse": self.warehouse,
			"basic_rate": 0,
		}
		if self.old_serial_number:
			item_row["serial_no"] = self.old_serial_number

		se.append("items", item_row)
		se.flags.ignore_permissions = True
		se.insert()
		se.submit()

		self.db_set("inward_stock_entry", se.name)

	def update_warranty_registration(self):
		"""Swap serial on Warranty Reg. Dates stay untouched."""
		if not self.warranty_registration or not self.new_serial_number:
			return

		reg = frappe.get_doc("Warranty Registration", self.warranty_registration)

		# Clear old Serial No link
		old_sn = reg.serial_number
		if old_sn and frappe.db.exists("Serial No", old_sn):
			frappe.db.set_value(
				"Serial No",
				old_sn,
				{"custom_warranty_registration": "", "custom_warranty_type": ""},
			)

		# Set new serial (DATES UNCHANGED — Track Changes logs this)
		reg.serial_number = self.new_serial_number

		# Sync new Serial No with warranty info
		if frappe.db.exists("Serial No", self.new_serial_number):
			frappe.db.set_value(
				"Serial No",
				self.new_serial_number,
				{
					"warranty_expiry_date": reg.warranty_end_date,
					"custom_warranty_type": reg.warranty_type,
					"custom_warranty_registration": reg.name,
				},
			)

		reg.flags.ignore_permissions = True
		reg.save()
