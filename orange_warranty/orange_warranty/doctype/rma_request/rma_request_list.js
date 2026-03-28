frappe.listview_settings["RMA Request"] = {
	get_indicator(doc) {
		const map = {
			Pending: ["Pending", "orange"],
			Approved: ["Approved", "blue"],
			Rejected: ["Rejected", "red"],
			"Replacement Dispatched": ["Dispatched", "purple"],
			"Faulty Received": ["Faulty Received", "yellow"],
			"Returned to Parent": ["Returned", "cyan"],
			Discarded: ["Discarded", "grey"],
			Closed: ["Closed", "green"],
		};
		const m = map[doc.rma_status];
		return m ? [__(m[0]), m[1], "rma_status,=," + doc.rma_status] : null;
	},
};
