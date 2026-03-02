import frappe
from frappe.tests import UnitTestCase
from frappe.utils import add_months, today, add_days


class TestRMARequest(UnitTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls._setup_test_data()

	@classmethod
	def _setup_test_data(cls):
		if not frappe.db.exists("Item Group", "Head"):
			frappe.get_doc({"doctype": "Item Group", "item_group_name": "Head", "parent_item_group": "All Item Groups"}).insert()
			frappe.db.commit()
		if not frappe.db.exists("Item", "TEST-HEAD-001"):
			frappe.get_doc({
				"doctype": "Item",
				"item_code": "TEST-HEAD-001",
				"item_name": "Test Head Item",
				"item_group": "Head",
				"has_serial_no": 1,
				"stock_uom": "Nos",
			}).insert()
			frappe.db.commit()
		if not frappe.db.exists("Customer", "Test RMA Customer"):
			frappe.get_doc({
				"doctype": "Customer",
				"customer_name": "Test RMA Customer",
				"customer_group": "All Customer Groups",
				"territory": "All Territories",
			}).insert()
			frappe.db.commit()

	def get_warehouse(self):
		company = frappe.db.get_single_value("Global Defaults", "default_company") or frappe.db.get_all("Company", limit=1)[0].name
		warehouses = frappe.db.get_all("Warehouse", filters={"company": company, "is_group": 0}, limit=1)
		return warehouses[0].name if warehouses else "Stores - _TC"

	def make_warranty_registration(self, **kwargs):
		wh = self.get_warehouse()
		wr = frappe.get_doc({
			"doctype": "Warranty Registration",
			"category": kwargs.get("category", "Head"),
			"item_code": "TEST-HEAD-001",
			"customer": "Test RMA Customer",
			"warranty_start_date": kwargs.get("warranty_start_date", today()),
			"warranty_end_date": kwargs.get("warranty_end_date", add_months(today(), 12)),
			"warranty_type": kwargs.get("warranty_type", "Orange Warranty"),
			"warehouse": wh,
			"quantity": 1,
		})
		wr.insert()
		return wr

	def make_rma_request(self, wr=None, **kwargs):
		if not wr:
			wr = self.make_warranty_registration(**kwargs)
		rma = frappe.get_doc({
			"doctype": "RMA Request",
			"warranty_registration": wr.name,
			"fault_description": kwargs.get("fault_description", "Test fault - unit not powering on"),
			"replacement_source": kwargs.get("replacement_source", "Own Stock"),
		})
		rma.insert()
		return rma

	def test_rma_creation_under_warranty(self):
		rma = self.make_rma_request()
		self.assertEqual(rma.is_under_warranty, 1)
		self.assertEqual(rma.is_foc, 1)
		self.assertEqual(rma.director_approval_required, 0)
		self.assertEqual(rma.director_approval_status, "Not Required")
		self.assertEqual(rma.rma_status, "Pending")

	def test_rma_creation_expired_warranty(self):
		rma = self.make_rma_request(
			warranty_start_date=add_days(today(), -400),
			warranty_end_date=add_days(today(), -30),
		)
		self.assertEqual(rma.is_under_warranty, 0)
		self.assertEqual(rma.is_foc, 0)
		self.assertEqual(rma.director_approval_required, 1)
		self.assertEqual(rma.director_approval_status, "Pending")

	def test_rma_negative_replacement_cost(self):
		wr = self.make_warranty_registration(
			warranty_start_date=add_days(today(), -400),
			warranty_end_date=add_days(today(), -30),
		)
		with self.assertRaises(frappe.exceptions.ValidationError):
			rma = frappe.get_doc({
				"doctype": "RMA Request",
				"warranty_registration": wr.name,
				"fault_description": "Test fault",
				"replacement_source": "Own Stock",
				"replacement_cost": -100,
			})
			rma.insert()

	def test_rma_submit_under_warranty(self):
		rma = self.make_rma_request()
		rma.rma_status = "Approved"
		rma.save()
		rma.submit()
		self.assertEqual(rma.docstatus, 1)
		self.assertEqual(rma.old_serial_number or "", rma.serial_number or "")

	def test_rma_submit_blocks_without_director_approval(self):
		rma = self.make_rma_request(
			warranty_start_date=add_days(today(), -400),
			warranty_end_date=add_days(today(), -30),
		)
		rma.rma_status = "Approved"
		rma.save()
		with self.assertRaises(frappe.exceptions.ValidationError):
			rma.submit()

	def test_rma_submit_with_director_approval(self):
		rma = self.make_rma_request(
			warranty_start_date=add_days(today(), -400),
			warranty_end_date=add_days(today(), -30),
		)
		rma.rma_status = "Approved"
		rma.director_approval_status = "Approved"
		rma.save()
		rma.submit()
		self.assertEqual(rma.docstatus, 1)

	def test_fetched_fields(self):
		wr = self.make_warranty_registration(warranty_type="Orange Warranty")
		rma = self.make_rma_request(wr=wr)
		self.assertEqual(rma.customer, wr.customer)
		self.assertEqual(rma.item_code, wr.item_code)
		self.assertEqual(rma.category, wr.category)
		self.assertEqual(rma.warranty_type, wr.warranty_type)
