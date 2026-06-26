frappe.ui.form.on('Lead', {
	refresh(frm) {
		add_wit_banner(frm);

		if (!frm.is_new()) {
			frm.add_custom_button(__('Decode VINs / Refresh Follow-Ups'), () => {
				frm.save();
			}, __('We Insure Things'));
		}

		if (frm.doc.custom_missing_information) {
			frm.dashboard.add_comment(__('Missing intake info: {0}', [frm.doc.custom_missing_information]), 'orange', true);
		}
	},

	custom_policy_type(frm) {
		if (frm.doc.custom_policy_type === 'Personal Auto' || frm.doc.custom_policy_type === 'Commercial Auto') {
			frm.toggle_display('custom_wit_vehicles', true);
		}
	}
});

function add_wit_banner(frm) {
	if (frm.dashboard.wrapper.find('.wit-insurance-banner').length) {
		return;
	}

	const policyType = frm.doc.custom_policy_type || 'Insurance lead';
	frm.dashboard.wrapper.prepend(`
		<div class="wit-insurance-banner">
			<strong>We Insure Things CRM</strong><br>
			<small>${frappe.utils.escape_html(policyType)} intake, follow-up, VIN, and call-summary workflow</small>
		</div>
	`);
}
