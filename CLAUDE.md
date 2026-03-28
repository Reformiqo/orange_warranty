CLAUDE.md — Orange O Tec: EMI Recalculation Feature

Project Context
Client: Orange O Tec Pvt Ltd (OOTPL)
Site: ootpl-m.frappe.cloud (ERPNext v16, Frappe Cloud hosted)
Feature: Purchase Payment Terms — EMI Recalculation
Scope: Purchase Order + Purchase Invoice
Deployment Method: Server Scripts + Client Scripts (no custom app needed)

---

What This Feature Does

Adds a "Recalculate EMI" button on Purchase Order and Purchase Invoice forms that:
Opens a dialog asking: number of EMIs, start date, day of month
Calculates outstanding = Grand Total − Advance − Delivery amounts
Splits outstanding into N equal monthly installments
Replaces only the EMI rows in Payment Schedule (preserves Advance/Delivery rows)
On PO: optionally cascades the same schedule to linked Purchase Invoices
Validates total = 100% and amount = grand_total before saving

Payment Structure Pattern
```
Advance (X%) + Delivery (Y%) + EMI 1..N (remaining %)  = 100%
```

Row Identification
A custom field `custom_payment_type` (Select: Advance / Delivery / EMI) on Payment Schedule child table distinguishes protected rows from replaceable EMI rows.

---

Formal Requirements

| DocType | Feature | Requirement |
|---------|---------|-------------|
| **Purchase Order** | EMI Recalc Button | Add a custom button labeled 'Recalculate EMI' on the Purchase Order form toolbar. Button visible only when document status is Draft, Submitted, or Partially Paid. |
| **Purchase Order** | EMI Input Dialog | On clicking 'Recalculate EMI', the system must display a modal dialog asking: (a) Total number of EMIs (integer, min 1), (b) Start date for EMI 1, (c) Day of month for recurring payments (e.g., 10). |
| **Purchase Order** | EMI Calculation | After input, system must calculate: Outstanding Amount = Invoice Total − Advance Paid − Delivery Payment. EMI Amount = Outstanding ÷ N. Each EMI date = Start Date + (n-1) months. |
| **Purchase Order** | EMI Calculation | Rounding: Last EMI = Outstanding − Sum(EMI 1 to N-1). This ensures total always equals outstanding amount exactly. |
| **Purchase Order** | Document Update | The new EMI schedule must REPLACE existing payment terms rows (EMI portion only) in the current document (PO or PI). Advance and Delivery rows must remain unchanged. |
| **Purchase Order** | Document Update | If a linked Purchase Invoice exists for the PO, the system must also update payment terms in all linked PIs automatically after user confirmation. |
| **Purchase Order** | Validation | System must validate: Total of all payment terms rows = 100% of invoice value. If mismatch > ₹1, show error and prevent save. |
| **Purchase Order** | Validation | System must prevent EMI recalculation if any EMI installment is already marked as 'Paid' in the Payment Schedule. |
| **Purchase Invoice** | EMI Recalc Button | Add the same 'Recalculate EMI' button on the Purchase Invoice form toolbar with identical behavior. |
| **Purchase Invoice** | EMI Input Dialog | On clicking 'Recalculate EMI', the system must display a modal dialog asking: (a) Total number of EMIs (integer, min 1), (b) Start date for EMI 1, (c) Day of month for recurring payments (e.g., 10). |
| **Purchase Invoice** | EMI Calculation | After input, system must calculate: Outstanding Amount = Invoice Total − Advance Paid − Delivery Payment. EMI Amount = Outstanding ÷ N. Each EMI date = Start Date + (n-1) months. |
| **Purchase Invoice** | EMI Calculation | Rounding: Last EMI = Outstanding − Sum(EMI 1 to N-1). This ensures total always equals outstanding amount exactly. |
| **Purchase Invoice** | Document Update | The new EMI schedule must REPLACE existing payment terms rows (EMI portion only) in the current document (PO or PI). Advance and Delivery rows must remain unchanged. |
| **Purchase Invoice** | Document Update | If a linked Purchase Invoice exists for the PO, the system must also update payment terms in all linked PIs automatically after user confirmation. |
| **Purchase Invoice** | Validation | System must validate: Total of all payment terms rows = 100% of invoice value. If mismatch > ₹1, show error and prevent save. |
| **Purchase Invoice** | Validation | System must prevent EMI recalculation if any EMI installment is already marked as 'Paid' in the Payment Schedule. |

> **Note:** "EMI portion" refers to the percentage remaining after Advance and Delivery rows. For example, if Advance = 20% and Delivery = 15%, then EMI portion = 65%. The exact split depends on the document's payment terms configuration.

---

Site Details

ERPNext Version: v16 (Frappe Cloud)
Database: MariaDB (Frappe Cloud managed)
Installed Apps: ERPNext, India Compliance (GST), Orange Warranty (custom)

Key Users:
`accounts@orangeotec.com` — Accounts team
`yash@orangeotec.com` — Yash (Purchase/Accounts)
`jyoti@orangeotec.com` — Jyoti (Sales/Accounts)
`sales-coordinator@orangeotec.com` — Sales Coordinator
`reformiqo@test.com` / `test@reformiqo.com` — Reformiqo dev/test

---

Architecture
```
┌─────────────────────────────────────────────────┐
│  Client Scripts (JS)                            │
│  ┌─────────────────┐  ┌──────────────────────┐  │
│  │ PO: EMI Button  │  │ PI: EMI Button       │  │
│  │ + Dialog + Conf │  │ + Dialog + Confirm   │  │
│  └────────┬────────┘  └──────────┬───────────┘  │
│           │                      │               │
│           └──────────┬───────────┘               │
│                      ▼                           │
│  ┌───────────────────────────────────────────┐   │
│  │ Server Script (API): recalculate_emi      │   │
│  │  - Validates inputs & permissions         │   │
│  │  - Identifies protected vs EMI rows       │   │
│  │  - Calculates EMI amounts + dates         │   │
│  │  - Replaces payment_schedule rows         │   │
│  │  - Cascades to linked PIs (if PO)         │   │
│  └───────────────────────────────────────────┘   │
│                                                   │
│  Client Scripts (Validation)                      │
│  ┌─────────────────┐  ┌──────────────────────┐   │
│  │ PO: validate()  │  │ PI: validate()       │   │
│  │ total = 100%    │  │ total = 100%         │   │
│  └─────────────────┘  └──────────────────────┘   │
└─────────────────────────────────────────────────┘
```

Files to Deploy (all via ERPNext UI, no bench needed)

#	Type	Name	DocType	Location in ERPNext
1	Custom Field	`custom_payment_type`	Payment Schedule	Setup → Custom Field
2	Server Script	Recalculate EMI	API (`recalculate_emi`)	Setup → Server Script
3	Client Script	EMI Recalculation - Purchase Order	Purchase Order (Form)	Setup → Client Script
4	Client Script	EMI Recalculation - Purchase Invoice	Purchase Invoice (Form)	Setup → Client Script
5	Client Script	Payment Validation - PO	Purchase Order (Form)	Setup → Client Script
6	Client Script	Payment Validation - PI	Purchase Invoice (Form)	Setup → Client Script

---

Custom Field Spec
```
DocType:       Payment Schedule (child table)
Label:         Payment Type
Fieldname:     custom_payment_type
Field Type:    Select
Options:       \nAdvance\nDelivery\nEMI
Insert After:  description
In List View:  Yes
```

---

Server Script: recalculate_emi

Type: API
Method: `recalculate_emi`
Allow Guest: No

Input Parameters (via `frappe.form_dict`)

Parameter	Type	Required	Description
`doctype`	str	Yes	"Purchase Order" or "Purchase Invoice"
`docname`	str	Yes	Document name (e.g., PUR-ORD-2026-00001)
`num_emis`	int	Yes	Number of EMI installments (min 1)
`start_date`	str	Yes	EMI 1 start date (YYYY-MM-DD)
`day_of_month`	int	Yes	Day for recurring payments (1-28)
`cascade_to_pi`	int	No	1 = update linked PIs, 0 = skip (default 0)

Core Logic
```python
# 1. Identify rows
protected_rows = rows where custom_payment_type IN ("Advance", "Delivery")
emi_rows = all other rows

# 2. Validate
- No EMI row should have paid_amount > 0
- Permission check (write on doctype)

# 3. Calculate
outstanding = grand_total - sum(protected_rows.payment_amount)
remaining_portion = 100 - sum(protected_rows.invoice_portion)
emi_base_amount = floor(outstanding / num_emis, 2)
last_emi = outstanding - (emi_base_amount * (num_emis - 1))  # rounding absorber

# 4. Generate dates
emi_date[i] = add_months(start_date, i) with day = min(day_of_month, month_max_day)

# 5. Replace
doc.payment_schedule = protected_rows + new_emi_rows
doc.save()  # with ignore_validate_update_after_submit for submitted docs

# 6. Cascade (PO only, if cascade_to_pi=1)
find linked PIs via Purchase Invoice Item.purchase_order
apply same EMI schedule with PI-specific amounts
```

Response
```json
{
  "success": true,
  "docname": "PUR-ORD-2026-00001",
  "num_emis": 6,
  "outstanding_amount": 650000,
  "emi_base_amount": 108333.33,
  "cascaded_invoices": ["PINV-26-00001"],
  "total_rows": 8
}
```

---

Client Script: Purchase Order (EMI Button)

Button Visibility
Shown when: document status is Draft, Submitted, or Partially Paid (i.e., `docstatus !== 2` AND `!frm.is_new()`)
Location: Actions → Recalculate EMI

Dialog Fields
HTML summary block (shows Grand Total, Advance+Delivery, EMI Split Amount)
`num_emis` (Int, required, default 6)
`start_date` (Date, required, default +1 month from today)
`day_of_month` (Int, required, default 10, range 1-28)
`cascade_to_pi` (Check, PO only, default unchecked)

Flow
```
Button click → Pre-check (paid EMIs?) → Dialog → Client validation →
Confirmation dialog → frappe.call("recalculate_emi") → Success msg → frm.reload_doc()
```

---

Client Script: Purchase Invoice (EMI Button)

Identical to PO script except:
No `cascade_to_pi` checkbox
`doctype` arg = "Purchase Invoice"
Function name: `show_emi_dialog_pi` (avoids collision)

---

Client Script: Validation (PO + PI)

Runs on `validate` event. Two separate Client Scripts (one per DocType).
```javascript
// Checks:
// 1. sum(invoice_portion) must be within 0.01 of 100%
// 2. sum(payment_amount) must be within ₹1 of grand_total
// If either fails: frappe.validated = false
```

---

Existing Client Scripts on PO (do not conflict)

These already exist on the site — our new scripts should coexist:
"Adding Bill of Landing & Buyer's Credit creation option in PO" — Adds Create → Bill of Landing and Create → Buyers Credit buttons. No conflict (different button group).
"Calculation due date in PO based on required by date" — Updates payment_schedule due dates when schedule_date changes. Currently commented out (`/* ... */`). No conflict.

---

Database Schema Reference

tabPayment Schedule (child table)
```sql
name              VARCHAR(140)  -- row ID
parent            VARCHAR(140)  -- parent doc name (PO/PI name)
parentfield       VARCHAR(140)  -- "payment_schedule"
parenttype        VARCHAR(140)  -- "Purchase Order" / "Purchase Invoice"
idx               INT           -- row order (1-based)
payment_term      VARCHAR(140)  -- link to Payment Term master
description       TEXT          -- display text
due_date          DATE          -- payment due date
invoice_portion   DECIMAL(21,9) -- percentage (e.g., 20.000000000)
payment_amount    DECIMAL(21,9) -- calculated amount
outstanding       DECIMAL(21,9) -- remaining to pay
paid_amount       DECIMAL(21,9) -- already paid
base_payment_amount DECIMAL(21,9) -- in base currency
mode_of_payment   VARCHAR(140)  -- optional
-- Custom field (to be added):
custom_payment_type VARCHAR(140) -- "Advance" / "Delivery" / "EMI"
```

Existing Payment Terms Masters
Site has many Payment Term records: "ADVANCE", "BALANCE AMOUNT", "1 Days" through "120 Days", percentage-based terms like "10%", "15", "75".

Sample Data Pattern
```
PUR-ORD-2026-00003:
  Row 1: ADVANCE       | 30% | ₹22,800  | 2025-05-14
  Row 2: BALANCE AMOUNT | 70% | ₹53,200  | 2025-07-05
```

Most POs/PIs currently use single-row 100% payment terms. The multi-row pattern (Advance + Balance) exists but is not yet structured with the custom_payment_type field.

---

Key Considerations & Edge Cases

Frappe Cloud Constraints
No bench access — everything via UI (Server Script, Client Script, Custom Field)
`import calendar` in Server Script — works in Frappe Server Scripts but if restricted, replace with:
```python
  last_day = frappe.utils.get_last_day("{0}-{1:02d}-01".format(year, month))
  max_day = frappe.utils.getdate(last_day).day
```
Server Script length limit — Frappe Cloud has no hard limit on Server Script size, but keep it reasonable

Submitted Document Updates
Uses `doc.flags.ignore_validate_update_after_submit = True` to allow payment schedule changes on submitted POs/PIs
This is the same pattern ERPNext uses internally for Payment Entry reconciliation
Risk: bypasses some standard validations — acceptable for this use case since we run our own validation

Rounding
`frappe.utils.flt(value, 2)` for amounts (2 decimal places)
`frappe.utils.flt(value, 3)` for portions (3 decimal places)
Last EMI absorbs all rounding: `last = total - sum(first_N-1)`
Final validation: if abs(total - 100) > 0.01 or abs(amount - grand_total) > 1 → throw

Cascade to PI
Finds linked PIs via: `frappe.get_all("Purchase Invoice Item", filters={"purchase_order": docname})`
Applies same EMI dates but recalculates amounts based on each PI's own grand_total
Skips PIs with paid EMI rows (warns instead of erroring)
Only available from PO, not from PI

Payment Type Tagging
Critical prerequisite: Existing Advance/Delivery rows MUST be tagged with `custom_payment_type` before first use
Any untagged row is treated as an EMI row and WILL BE REPLACED
Consider a one-time data migration script to tag existing rows

---

Testing Checklist

Setup Verification
[ ] Custom field `custom_payment_type` visible in Payment Schedule child table
[ ] Server Script created, API method accessible
[ ] Client Script buttons appear on PO and PI forms
[ ] No console errors on form load

Functional Tests
[ ] Create PO with Advance (20%) + Delivery (15%) + Balance (65%) — tag types
[ ] Click Recalculate EMI → 6 EMIs, start next month, day 10
[ ] Verify: Advance + Delivery rows unchanged, 6 EMI rows created
[ ] Verify: All portions sum to 100%, all amounts sum to grand_total
[ ] Verify: Last EMI has rounding adjustment
[ ] Verify: EMI dates are correct (monthly, correct day)

Edge Cases
[ ] Day 31 → should use last day of shorter months (Feb=28, Apr=30)
[ ] 1 EMI → entire outstanding in single row
[ ] Submitted PO → should work with ignore_validate flag
[ ] PO with linked PI → cascade updates PI payment schedule
[ ] PI with paid EMI row → cascade skips with warning
[ ] Cancelled document → button should NOT appear
[ ] New/unsaved document → button should NOT appear

Validation Tests
[ ] Try saving with portions ≠ 100% → should block
[ ] Try recalculating when EMI has payments → should block
[ ] Try with non-write-permission user → should block

---

Slash Commands for Claude Code
```
/deploy-emi    — Walk through deploying all 6 artifacts to the site
/test-emi      — Generate test scenarios and verify on the demo site
/fix-emi       — Debug a reported issue with EMI recalculation
/tag-existing  — Script to bulk-tag existing payment rows with custom_payment_type
```

---

File Inventory

File	Purpose
`orange_warranty/api_emi.py`	Server-side EMI recalculation logic (API endpoint)
`orange_warranty/public/js/purchase_order.js`	Client Script for Purchase Order (EMI button + dialog + validation)
`orange_warranty/public/js/purchase_invoice.js`	Client Script for Purchase Invoice (EMI button + dialog + validation)
`orange_warranty/setup.py`	Custom field creation (`custom_payment_type` on Payment Schedule)
`orange_warranty/hooks.py`	Module integration (doctype_js mappings, fixtures)
`CLAUDE.md`	This file — Claude Code context and formal requirements
