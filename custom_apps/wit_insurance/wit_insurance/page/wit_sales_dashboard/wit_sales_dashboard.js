frappe.pages['wit-sales-dashboard'].on_page_load = function(wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'WIT Sales Dashboard',
		single_column: true
	});

	page.main.html(`
		<div class="wit-sales-page">
			<div class="wit-sales-hero">
				<div>
					<div class="eyebrow">We Insure Things</div>
					<h2>Sales Tracker</h2>
					<p>Track bound premium, commission, policies, producers, carriers, and daily momentum.</p>
				</div>
				<div class="wit-sales-actions">
					<select class="form-control" id="wit-sales-scope">
						<option value="agency">Agency</option>
						<option value="mine">Mine</option>
					</select>
					<select class="form-control" id="wit-sales-period">
						<option value="MTD">MTD</option>
						<option value="YTD">YTD</option>
						<option value="ALL">All</option>
					</select>
					<button class="btn btn-primary" id="wit-add-sale">Log Sale</button>
					<button class="btn btn-default" id="wit-refresh-sales">Refresh</button>
				</div>
			</div>

			<div class="wit-kpi-grid">
				<div class="wit-kpi"><div class="label">Bound Premium</div><div class="value" id="wit-kpi-premium">$0</div><div class="sub" id="wit-kpi-period">MTD</div></div>
				<div class="wit-kpi"><div class="label">Commission</div><div class="value" id="wit-kpi-commission">$0</div><div class="sub">calculated from rate</div></div>
				<div class="wit-kpi"><div class="label">Policies</div><div class="value" id="wit-kpi-policies">0</div><div class="sub">bound</div></div>
				<div class="wit-kpi"><div class="label">Today</div><div class="value" id="wit-kpi-today">$0</div><div class="sub" id="wit-kpi-today-count">0 policies</div></div>
			</div>

			<div class="wit-sales-grid">
				<div class="wit-card">
					<div class="wit-card-head"><h3>Recent Sales</h3><input class="form-control" id="wit-sale-search" placeholder="Search sales"></div>
					<div class="table-responsive"><table class="table table-hover"><thead><tr><th>Date</th><th>Customer</th><th>Producer</th><th>Line</th><th>Carrier</th><th>Status</th><th>Premium</th><th>Commission</th></tr></thead><tbody id="wit-sales-rows"></tbody></table></div>
				</div>
				<div class="wit-card">
					<div class="wit-card-head"><h3>Leaderboard</h3><select class="form-control" id="wit-leader-metric"><option value="premium">Premium</option><option value="commission">Commission</option><option value="policies">Policies</option></select></div>
					<div id="wit-leaderboard"></div>
				</div>
			</div>
		</div>
	`);

	const state = { scope: 'agency', period: 'MTD', metric: 'premium', search: '' };

	function money(value) {
		return format_currency(value || 0, frappe.defaults.get_default('currency') || 'USD');
	}

	function load() {
		state.scope = page.main.find('#wit-sales-scope').val();
		state.period = page.main.find('#wit-sales-period').val();
		state.metric = page.main.find('#wit-leader-metric').val();
		state.search = page.main.find('#wit-sale-search').val() || '';

		frappe.call({
			method: 'wit_insurance.sales_dashboard.summary',
			args: { scope: state.scope, period: state.period },
			callback(r) {
				const s = r.message || {};
				page.main.find('#wit-kpi-premium').text(money(s.mtdPremium));
				page.main.find('#wit-kpi-commission').text(money(s.mtdCommission));
				page.main.find('#wit-kpi-policies').text(s.mtdPolicies || 0);
				page.main.find('#wit-kpi-today').text(money(s.todayPremium));
				page.main.find('#wit-kpi-today-count').text(`${s.todayPolicies || 0} policies`);
				page.main.find('#wit-kpi-period').text(`${s.period || state.period} · ${s.from_date || ''} to ${s.to_date || ''}`);
			}
		});

		frappe.call({
			method: 'wit_insurance.sales_dashboard.list_sales',
			args: { scope: state.scope, period: state.period, search: state.search },
			callback(r) {
				renderSales(r.message || []);
			}
		});

		frappe.call({
			method: 'wit_insurance.sales_dashboard.leaderboard',
			args: { scope: state.scope, period: state.period, metric: state.metric },
			callback(r) {
				renderLeaderboard((r.message || {}).rows || []);
			}
		});
	}

	function renderSales(rows) {
		const tbody = page.main.find('#wit-sales-rows');
		if (!rows.length) {
			tbody.html('<tr><td colspan="8" class="text-muted text-center">No sales found.</td></tr>');
			return;
		}
		tbody.html(rows.map(row => `
			<tr data-name="${frappe.utils.escape_html(row.name)}">
				<td>${frappe.datetime.str_to_user(row.sales_date || '')}</td>
				<td><a href="/app/wit-sale/${encodeURIComponent(row.name)}">${frappe.utils.escape_html(row.customer || '')}</a></td>
				<td>${frappe.utils.escape_html(row.producer_name || row.producer || '')}</td>
				<td>${frappe.utils.escape_html(row.line || '')}</td>
				<td>${frappe.utils.escape_html(row.carrier || '')}</td>
				<td><span class="wit-pill ${String(row.status || '').toLowerCase()}">${frappe.utils.escape_html(row.status || '')}</span></td>
				<td>${money(row.premium)}</td>
				<td>${money(row.commission)}</td>
			</tr>
		`).join(''));
	}

	function renderLeaderboard(rows) {
		const box = page.main.find('#wit-leaderboard');
		if (!rows.length) {
			box.html('<div class="wit-empty">No leaderboard data yet.</div>');
			return;
		}
		const max = Math.max(...rows.map(r => flt(r.value))) || 1;
		box.html(rows.map((row, i) => {
			const value = flt(row.value);
			const pct = Math.max(4, Math.round(value / max * 100));
			const display = state.metric === 'policies' ? value : money(value);
			return `<div class="wit-leader-row"><div><strong>${i + 1}. ${frappe.utils.escape_html(row.producer || 'Unassigned')}</strong><span>${display}</span></div><div class="wit-bar"><i style="width:${pct}%"></i></div></div>`;
		}).join(''));
	}

	function openSaleDialog() {
		const dialog = new frappe.ui.Dialog({
			title: 'Log WIT Sale',
			fields: [
				{ fieldname: 'customer', label: 'Customer', fieldtype: 'Data', reqd: 1 },
				{ fieldname: 'sales_date', label: 'Date', fieldtype: 'Date', default: frappe.datetime.get_today(), reqd: 1 },
				{ fieldname: 'line', label: 'Line', fieldtype: 'Select', options: '\nAuto\nHome\nBundle (Auto+Home)\nRenters\nCommercial\nGeneral Liability\nWorkers Comp\nLife\nHealth\nUmbrella\nOther' },
				{ fieldname: 'carrier', label: 'Carrier', fieldtype: 'Data' },
				{ fieldname: 'business_type', label: 'Type', fieldtype: 'Select', options: '\nNew\nRenewal\nRewrite\nCross-Sell\nUpsell\nReinstatement\nOther' },
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
					callback() {
						dialog.hide();
						frappe.show_alert({ message: 'Sale logged', indicator: 'green' });
						load();
					}
				});
			}
		});
		dialog.show();
	}

	page.main.find('#wit-sales-scope, #wit-sales-period, #wit-leader-metric').on('change', load);
	page.main.find('#wit-sale-search').on('input', frappe.utils.debounce(load, 300));
	page.main.find('#wit-refresh-sales').on('click', load);
	page.main.find('#wit-add-sale').on('click', openSaleDialog);
	load();
};
