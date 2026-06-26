frappe.ui.form.on('Lead', {
	refresh(frm) {
		add_wit_banner(frm);

		if (!frm.is_new()) {
			frm.add_custom_button(__('Decode VINs / Refresh Follow-Ups'), () => {
				frm.save();
			}, __('We Insure Things'));

			frm.add_custom_button(__('Log Sale'), () => {
				open_sale_dialog_from_lead(frm);
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
			<small>${frappe.utils.escape_html(policyType)} intake, follow-up, VIN, call-summary, and sales workflow</small>
		</div>
	`);
}

function open_sale_dialog_from_lead(frm) {
	const customer = frm.doc.lead_name || `${frm.doc.first_name || ''} ${frm.doc.last_name || ''}`.trim() || frm.doc.company_name;
	const line = map_policy_type_to_line(frm.doc.custom_policy_type);
	const dialog = new frappe.ui.Dialog({
		title: 'Log WIT Sale',
		fields: [
			{ fieldname: 'customer', label: 'Customer', fieldtype: 'Data', reqd: 1, default: customer },
			{ fieldname: 'lead', label: 'Lead', fieldtype: 'Link', options: 'Lead', default: frm.doc.name, read_only: 1 },
			{ fieldname: 'sales_date', label: 'Date', fieldtype: 'Date', default: frappe.datetime.get_today(), reqd: 1 },
			{ fieldname: 'line', label: 'Line', fieldtype: 'Select', options: '\nAuto\nHome\nBundle (Auto+Home)\nRenters\nCommercial\nGeneral Liability\nWorkers Comp\nLife\nHealth\nUmbrella\nOther', default: line },
			{ fieldname: 'carrier', label: 'Carrier', fieldtype: 'Data' },
			{ fieldname: 'business_type', label: 'Type', fieldtype: 'Select', options: '\nNew\nRenewal\nRewrite\nCross-Sell\nUpsell\nReinstatement\nOther', default: 'New' },
			{ fieldname: 'status', label: 'Status', fieldtype: 'Select', options: 'Quoted\nPending\nBound\nLost\nCancelled', default: 'Bound' },
			{ fieldname: 'premium', label: 'Premium', fieldtype: 'Currency' },
			{ fieldname: 'commission_rate', label: 'Commission Rate', fieldtype: 'Percent' },
			{ fieldname: 'notes', label: 'Notes', fieldtype: 'Small Text' }
		],
		primary_action_label: 'Save Sale',
		primary_action(values) {
			frappe.call({
				method: 'wit_insurance.sales_dashboard.create_sale',
				args: values,
				callback(response) {
					dialog.hide();
					frappe.show_alert({ message: 'Sale logged', indicator: 'green' });
					if (response.message && response.message.name) {
						frappe.set_route('Form', 'WIT Sale', response.message.name);
					}
				}
			});
		}
	});
	dialog.show();
}

function map_policy_type_to_line(policyType) {
	const map = {
		'Personal Auto': 'Auto',
		'Commercial Auto': 'Commercial',
		'Home': 'Home',
		'Renters': 'Renters',
		'General Liability': 'General Liability',
		'Workers Compensation': 'Workers Comp'
	};
	return map[policyType] || 'Other';
}
