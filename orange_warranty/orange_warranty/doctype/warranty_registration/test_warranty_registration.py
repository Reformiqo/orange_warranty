import frappe
from frappe.tests import UnitTestCase
from frappe.utils import add_days, add_months, today


class TestWarrantyRegistration(UnitTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls._setup_test_data()

	@classmethod
	def _setup_test_data(cls):
		if not frappe.db.exists("Item Group", "All Item Groups"):
			frappe.get_doc(
				{"doctype": "Item Group", "item_group_name": "All Item Groups", "is_group": 1}
			).insert(ignore_permissions=True)
			frappe.db.commit()  # nosemgrep
		if not frappe.db.exists("Item Group", "Head"):
			frappe.get_doc(
				{"doctype": "Item Group", "item_group_name": "Head", "parent_item_group": "All Item Groups"}
			).insert()
			frappe.db.commit()  # nosemgrep
		if not frappe.db.exists("Item", "TEST-HEAD-001"):
			frappe.get_doc(
				{
					"doctype": "Item",
					"item_code": "TEST-HEAD-001",
					"item_name": "Test Head Item",
					"item_group": "Head",
					"has_serial_no": 1,
					"stock_uom": "Nos",
				}
			).insert()
			frappe.db.commit()  # nosemgrep
		if not frappe.db.exists("Customer", "Test WR Customer"):
			frappe.get_doc(
				{
					"doctype": "Customer",
					"customer_name": "Test WR Customer",
					"customer_group": "All Customer Groups",
					"territory": "All Territories",
				}
			).insert()
			frappe.db.commit()  # nosemgrep

	def get_warehouse(self):
		company = (
			frappe.db.get_single_value("Global Defaults", "default_company")
			or frappe.db.get_all("Company", limit=1)[0].name
		)
		warehouses = frappe.db.get_all("Warehouse", filters={"company": company, "is_group": 0}, limit=1)
		return warehouses[0].name if warehouses else "Stores - _TC"

	def make_warranty_registration(self, **kwargs):
		wh = self.get_warehouse()
		wr = frappe.get_doc(
			{
				"doctype": "Warranty Registration",
				"category": kwargs.get("category", "Head"),
				"item_code": kwargs.get("item_code", "TEST-HEAD-001"),
				"serial_number": kwargs.get("serial_number"),
				"customer": kwargs.get("customer", "Test WR Customer"),
				"warranty_start_date": kwargs.get("warranty_start_date", today()),
				"warranty_end_date": kwargs.get("warranty_end_date", add_months(today(), 12)),
				"warranty_type": kwargs.get("warranty_type", "Orange Warranty"),
				"warehouse": kwargs.get("warehouse", wh),
				"quantity": 1,
			}
		)
		wr.insert()
		return wr

	def test_warranty_registration_creation(self):
		wr = self.make_warranty_registration()
		self.assertTrue(wr.name.startswith("WR-Head-"))
		self.assertEqual(wr.warranty_status, "Active")
		self.assertGreater(wr.remaining_warranty_days, 0)

	def test_warranty_date_validation(self):
		with self.assertRaises(frappe.exceptions.ValidationError):
			self.make_warranty_registration(
				warranty_start_date=today(),
				warranty_end_date=add_days(today(), -10),
			)

	def test_expired_warranty(self):
		wr = self.make_warranty_registration(
			warranty_start_date=add_days(today(), -400),
			warranty_end_date=add_days(today(), -30),
		)
		self.assertEqual(wr.warranty_status, "Expired")
		self.assertEqual(wr.remaining_warranty_days, 0)

	def test_active_warranty_status(self):
		wr = self.make_warranty_registration(
			warranty_start_date=today(),
			warranty_end_date=add_months(today(), 6),
		)
		self.assertEqual(wr.warranty_status, "Active")
		self.assertGreater(wr.remaining_warranty_days, 0)
