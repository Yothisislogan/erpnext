# WIT Insurance CRM Port Review for ERPNext

## Bottom line

Yes, the SuiteCRM insurance CRM work can be ported to this ERPNext/Frappe fork, but it should not be moved line-for-line. SuiteCRM is PHP/vardefs/logic-hooks. ERPNext is Python/Frappe DocTypes, Custom Fields, Communication, ToDo, hooks, and scheduled jobs.

The ERPNext version should be built as a WIT insurance customization layer on top of the standard `Lead` DocType, with the VOIP project writing call summaries/transcripts into Lead or Communication records.

## Why ERPNext is a good fit

The current repo is a fork of ERPNext on the `develop` branch. The ERPNext app metadata shows this is the main `erpnext` Frappe app and is licensed under GNU GPL v3.

Relevant standard features already present:

- `Lead` has normal CRM fields for name, email, phone, mobile, owner, status, source, address/city/state/country, qualification, notes, and activities.
- `Lead` has `email_append_to = 1`, which means inbound email/Communication can be attached to Lead records.
- ERPNext already links Communications and Events with CRM records through hooks.
- ERPNext already has `ToDo` and `Task` style activity records that can replace the SuiteCRM Task creation.
- ERPNext already exposes Frappe REST APIs, which is better for the VOIP project than custom SuiteCRM endpoints.

## Best implementation path

### Recommended: WIT custom Frappe app

Create a separate app named something like `wit_insurance` and install it beside ERPNext in the same bench.

This keeps WIT insurance logic separate from upstream ERPNext and avoids fighting merge conflicts whenever ERPNext updates. The app should contain:

```text
wit_insurance/
  hooks.py
  fixtures/custom_field.json
  public/js/lead_insurance.js
  wit_insurance/crm/lead_hooks.py
  wit_insurance/crm/email_parser.py
  wit_insurance/crm/vin.py
  wit_insurance/api/lead_intake.py
```

This is the cleanest replacement for the SuiteCRM custom extension approach.

### Acceptable short-term: modify this ERPNext fork

Because this is your fork, we can also add the insurance fields and hooks directly into `erpnext`. This is faster but less clean. It means future upstream ERPNext merges could conflict with WIT-specific changes.

## Mapping from SuiteCRM version to ERPNext version

| SuiteCRM feature | ERPNext/Frappe equivalent | Port approach |
| --- | --- | --- |
| Leads custom fields | Custom Field fixtures on `Lead` | Add fields through `fixtures/custom_field.json` in WIT app |
| Name | Existing `first_name`, `last_name`, `lead_name` | Use native fields |
| Email | Existing `email_id` | Use native field |
| Phone | Existing `phone`, `mobile_no` | Use native fields |
| Address | Existing address/city/state/country and Contact/Address links | Use native fields first; expand later if needed |
| Coverage limits | New custom field | `custom_coverage_limits` Text |
| Drivers DOB/DL | New child DocType or JSON field | Prefer child table: `WIT Driver` |
| Multiple VINs | New child DocType or JSON field | Prefer child table: `WIT Vehicle` |
| Accidents/violations | New child DocType or JSON field | Prefer child table: `WIT Incident` |
| Next action | Native ToDo plus custom summary field | Create ToDo linked to Lead |
| Scheduled follow up | ToDo `date` / Event / Task | Create linked ToDo automatically |
| Call summary | Communication or custom Long Text | Store transcript/summary in both Communication and `custom_call_summary` |
| Missing info extraction | Lead validate hook | Fill blanks from call summary/transcript |
| Conviction follow-up | Lead validate + ToDo creation | Calculate conviction date + 2 years + 11 months |
| VIN decoder | Python service using NHTSA vPIC | Server-side `requests.get()` and save decoded vehicle fields |
| Email parser | Communication after_insert hook or scheduled job | Parse incoming Communication from leads mailbox |
| VOIP integration | Frappe whitelisted API method | `/api/method/wit_insurance.api.lead_intake.upsert_lead_from_call` |

## Recommended Lead custom fields

Use native fields first wherever possible, then add these custom fields to `Lead`:

| Fieldname | Type | Purpose |
| --- | --- | --- |
| `custom_policy_type` | Select | Personal Auto, Commercial Auto, Home, Renters, GL, WC, BOP, Specialty |
| `custom_coverage_limits` | Small Text | Requested liability/coverage limits |
| `custom_drivers` | Table | Child table for drivers |
| `custom_vehicles` | Table | Child table for vehicles/VINs |
| `custom_accidents_violations` | Table | Child table for incidents |
| `custom_next_action` | Small Text | Agent's next step |
| `custom_next_follow_up` | Datetime | Scheduled follow-up date/time |
| `custom_call_summary` | Long Text | Call notes/transcript summary |
| `custom_missing_information` | Small Text | Auto-generated list of missing intake data |
| `custom_last_violation_conviction_date` | Date | Most recent conviction date |
| `custom_violation_follow_up_date` | Date | Conviction date + 2 years + 11 months |
| `custom_auto_followup_required` | Check | Flag for automated follow-up |
| `custom_vin_decode_status` | Small Text | NHTSA decode result summary |
| `custom_source_communication` | Link to Communication | Source email/call record |
| `custom_parse_confidence` | Select | High / Medium / Low |

## Recommended child DocTypes

### WIT Driver

Fields:

- Driver Name
- DOB
- Driver License Number
- Driver License State
- Relationship
- Notes

### WIT Vehicle

Fields:

- VIN
- Year
- Make
- Model
- Body Class
- Vehicle Type
- Manufacturer
- Decode Status

### WIT Incident

Fields:

- Incident Type: Accident / Violation / Ticket / Claim
- Incident Date
- Conviction Date
- Description
- At Fault
- Follow-up Date

## Email parsing design

ERPNext/Frappe stores inbound and outbound email as `Communication` records. The WIT app should hook into `Communication.after_insert` and look for messages sent to or from:

- `leads@weinsurethings.com`
- `leads@weinsruethings.com`

The second address is included only because it appeared in the original request. Remove it if it was a typo.

Parser behavior:

1. Read subject, sender, recipients, text content, and HTML content.
2. Extract name, email, phone, address, coverage limits, DOB, DL, VINs, accidents, violations, conviction dates, requested limits, next action, and follow-up dates.
3. Search for an existing Lead by email or phone.
4. Create or update Lead.
5. Link the source Communication to the Lead.
6. Run VIN decode for any VINs.
7. Calculate conviction follow-up dates.
8. Create linked ToDo records for follow-up.

## VOIP integration design

The VOIP project should not write directly to the ERPNext database. It should call a whitelisted Frappe method.

Recommended endpoint:

```text
/api/method/wit_insurance.api.lead_intake.upsert_lead_from_call
```

Expected payload:

```json
{
  "name": "Jane Smith",
  "email": "jane@example.com",
  "phone": "555-555-5555",
  "address": "123 Main St, Asheville, NC",
  "policy_type": "Personal Auto",
  "coverage_limits": "100/300/100",
  "drivers": [
    {"name": "Jane Smith", "dob": "1988-01-15", "driver_license": "NC1234567", "license_state": "NC"}
  ],
  "vehicles": [
    {"vin": "1HGCM82633A004352"}
  ],
  "incidents": [
    {"type": "Violation", "conviction_date": "2024-04-01", "description": "Speeding ticket"}
  ],
  "call_summary": "Customer wants personal auto quote with one prior speeding ticket.",
  "next_action": "Call back with quote options",
  "next_follow_up": "2026-06-30 09:00:00"
}
```

## VIN lookup

Use the free NHTSA vPIC VIN API for VIN decoding. Store the original VIN regardless of whether the lookup succeeds. If the lookup succeeds, save year, make, model, body class, vehicle type, and manufacturer.

## Accident and violation follow-up rule

When a conviction date exists:

```text
violation_follow_up_date = conviction_date + 2 years + 11 months
```

Then create a linked ToDo assigned to the lead owner:

```text
Subject: Re-shop / follow up on violation aging date
Reference Type: Lead
Reference Name: <lead>
Date: calculated follow-up date
```

## What not to do

Do not port the SuiteCRM PHP files directly.

Do not make the VOIP app scrape the ERPNext UI.

Do not make all driver/vehicle/incident data one giant text field long term. JSON is acceptable for a quick prototype, but child tables are better for reporting, filtering, and future quote automation.

Do not store full driver license numbers or dates of birth without role-based permissions and a retention policy. These are sensitive personal data.

## Suggested build phases

### Phase 1: MVP insurance Lead customization

- Add custom fields and child tables.
- Add Lead form UI improvements.
- Add VIN decode service.
- Add missing info detection.
- Add follow-up ToDo creation.

### Phase 2: Email intake

- Configure ERPNext email account for leads mailbox.
- Add Communication parser.
- Create/update Leads from inbound email.
- Attach source Communication to Lead.

### Phase 3: VOIP integration

- Add whitelisted API endpoint for call transcript payloads.
- Push call summary and structured extraction into Lead.
- Create ToDos from call outcomes.

### Phase 4: quoting workflow

- Convert qualified Lead into Opportunity.
- Add carrier/appetite fields.
- Add quote status, quote amount, bind date, and policy number.
- Add reporting dashboard for follow-up pipeline and missing information.

## Recommendation

Use ERPNext as the CRM, but put WIT insurance logic in a separate `wit_insurance` Frappe app instead of modifying upstream ERPNext core. This gives WIT the same practical flexibility we were aiming for in SuiteCRM, but in Python/Frappe with cleaner APIs for the VOIP project.
