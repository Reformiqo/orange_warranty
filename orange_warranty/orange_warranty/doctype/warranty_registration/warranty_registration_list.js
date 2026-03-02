frappe.listview_settings["Warranty Registration"] = {
	get_indicator(doc) {
		if (doc.warranty_status === "Active")
			return [__("Active"), "green", "warranty_status,=,Active"];
		return [__("Expired"), "red", "warranty_status,=,Expired"];
	},
};
