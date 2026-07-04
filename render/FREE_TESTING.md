# Free CRM testing options

The free path is local testing on your own computer, not Render free.

## Best free option

Use a local Docker/Frappe bench on your desktop or laptop.

This lets you test:

- WIT Insurance Settings
- WIT Intake Review
- Lead creation and conversion
- Email parsing logic
- VOIP intake endpoint token checks
- Sales dashboard permissions

## Why not Render Free

Render Free is not a good fit for ERPNext/Frappe because the CRM needs database and file persistence. Render Free web services spin down and lose local filesystem changes. Render persistent disks require a paid service.

## Local test outline

1. Install Docker Desktop.
2. Clone this repo.
3. Use Frappe Docker or a local Frappe bench.
4. Copy `custom_apps/wit_insurance` into the bench apps folder.
5. Install ERPNext and then install the WIT app.
6. Run migrate, build, and restart.

## Bench commands after the bench exists

```bash
bench get-app erpnext /path/to/this/repo
cp -a /path/to/this/repo/custom_apps/wit_insurance ./apps/wit_insurance
bench --site your-site.local install-app erpnext
bench --site your-site.local install-app wit_insurance
bench --site your-site.local migrate
bench build
bench restart
```

## Test the VOIP endpoint locally

```bash
curl -X POST "http://localhost:8000/api/method/wit_insurance.lead_intake.upsert_lead_from_call" \
  -H "Content-Type: application/json" \
  -H "X-WIT-VOIP-Token: YOUR_TOKEN" \
  -d '{"name":"Test Lead","phone":"828-555-1212","policy_type":"Renters"}'
```

Set the token first in WIT Insurance Settings.

## Recommendation

Use local testing for free. Use Render only if you are willing to pay for a small service plus persistent disk. Use Hetzner for production.
