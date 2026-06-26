# WIT Insurance CRM for ERPNext

This is a portable Frappe custom app scaffold for turning ERPNext into a We Insure Things branded insurance CRM.

It is intentionally separate from ERPNext core logic. The goal is to install this beside ERPNext in a bench, not permanently fork ERPNext every time WIT needs an insurance workflow change.

## What this MVP adds

- Insurance intake fields on ERPNext `Lead`
- Driver child table
- Vehicle / VIN child table
- Accident / violation child table
- Call summary and next-action fields
- Missing-information detection
- Conviction-date aging follow-up rule
- Free NHTSA vPIC VIN decode service
- Inbound email parsing from `leads@weinsurethings.com`
- API endpoint for the VOIP/call-transcript project
- WIT brand color layer using `#00AEEF`
- `WIT Insurance Settings` page
- `WIT Intake Review` queue for parsed emails and VOIP payloads
- Duplicate lead matching by email, phone, VIN, and name/ZIP
- Native ERPNext/Frappe port of the WIT Sales Tracker dashboard
- `WIT Sale` records for premium, commission, policy count, producer, carrier, line, and status tracking

## Sales dashboard

The previous SuiteCRM branch contained a standalone Flask/SQLite sales tracker with an HTML dashboard. This app ports the useful pieces into Frappe instead of running a separate Flask app.

New DocType:

```text
WIT Sale
```

New Desk page:

```text
/app/wit-sales-dashboard
```

Dashboard features included in the Frappe version:

```text
Bound premium
Commission
Policy count
Today premium
Recent sales table
Producer leaderboard
Agency vs mine scope
MTD / YTD / All periods
Log Sale dialog
Lead -> Log Sale button
```

The Flask-specific pieces were intentionally not copied because Frappe already handles authentication, users, permissions, database records, audit/change history, and Desk pages.

## Correct lead mailbox

Use only:

```text
leads@weinsurethings.com
```

This is configurable in `WIT Insurance Settings`, but the default is the correct WIT mailbox above.

## WIT Insurance Settings

The settings page controls:

```text
Lead Mailbox
Default Lead Owner
Default Follow-Up Owner
Enable VIN Decode
Require Intake Review Before Creating Lead
Violation Follow-Up Months
VOIP API Token
Duplicate Match Lookback Days
```

Default follow-up rule:

```text
conviction date + 35 months
```

## Intake review workflow

By default, incoming email and VOIP payloads do not immediately create Leads. They create a `WIT Intake Review` record first.

Agents can review parsed data, possible duplicate matches, missing information, and then choose:

```text
Approve to Lead
Reject
Open Lead
```

This prevents bad parses from silently polluting the CRM.

## Install path

Long term, this should live in its own repository named something like:

```text
Yothisislogan/wit_insurance
```

For now it is staged inside this ERPNext fork under:

```text
custom_apps/wit_insurance
```

To test in a bench, move or copy this folder to:

```text
frappe-bench/apps/wit_insurance
```

Then run:

```bash
bench --site your-site.local install-app wit_insurance
bench --site your-site.local migrate
bench build
bench restart
```

## VOIP endpoint

After install, the VOIP app should POST to:

```text
/api/method/wit_insurance.lead_intake.upsert_lead_from_call
```

If `VOIP API Token` is set in WIT Insurance Settings, requests must include:

```text
X-WIT-VOIP-Token: your-token
```

or:

```text
Authorization: Bearer your-token
```

## Example payload

```json
{
  "name": "Jane Smith",
  "email": "jane@example.com",
  "phone": "555-555-5555",
  "address": "123 Main St, Asheville, NC",
  "policy_type": "Personal Auto",
  "coverage_limits": "100/300/100",
  "drivers": [
    {
      "driver_name": "Jane Smith",
      "date_of_birth": "1988-01-15",
      "driver_license_number": "NC1234567",
      "driver_license_state": "NC"
    }
  ],
  "vehicles": [
    {"vin": "1HGCM82633A004352"}
  ],
  "incidents": [
    {
      "incident_type": "Violation",
      "conviction_date": "2024-04-01",
      "description": "Speeding ticket"
    }
  ],
  "call_summary": "Customer wants personal auto quote with one speeding ticket.",
  "next_action": "Call back with quote options",
  "next_follow_up": "2026-06-30 09:00:00"
}
```

## Security note

Driver DOBs and license numbers are sensitive. Before production, restrict field visibility by role, confirm retention rules, and avoid exposing these fields through public forms or unauthenticated API calls.
