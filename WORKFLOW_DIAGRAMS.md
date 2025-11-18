# Workflow Diagram - Offer Letter Confirmation

## High-Level Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ User opens admin_approved_candidates.html                       │
│ Selects a candidate from approved_candidates                    │
│ Clicks view profile → offer letter → "Confirm & Send" button    │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
            ┌───────────────────────┐
            │ showOfferLetterModal  │
            │ Display PDF in modal  │
            │ Show "Confirm" button │
            └───────────┬───────────┘
                        │
                        │ User clicks "✓ Confirm & Send"
                        ▼
        ┌───────────────────────────────┐
        │ confirmOfferLetter()           │
        │ Close modal                    │
        │ Prepare two API calls          │
        └───────────┬───────────────────┘
                    │
        ┌───────────┴───────────┐
        │                       │
        ▼                       ▼
    ┌─────────────────┐   ┌──────────────────┐
    │ STEP 1: EMAIL   │   │ STEP 2: TRANSFER │
    │ (Independent)   │   │ (Independent)    │
    └────────┬────────┘   └────────┬─────────┘
             │                      │
             │ POST /admin/api/     │ POST /admin/api/
             │ send-offer-email    │ transfer-to-selected
             │                      │
             ▼                      ▼
    ┌─────────────────────────────────────┐
    │ Backend Processing                  │
    │                                     │
    │ Email Endpoint:                     │
    │ - Decode PDF from base64            │
    │ - Call send_offer_letter_email()    │
    │ - Log result                        │
    │ - Return success/error              │
    │                                     │
    │ Transfer Endpoint:                  │
    │ - Find approved_candidate by USN    │
    │ - Check if already in Selected      │
    │ - Generate candidate_id             │
    │ - Populate Selected record          │
    │ - Store offer letter PDF            │
    │ - Delete from approved_candidates   │
    │ - Return success/error              │
    └────────────┬────────────────────────┘
                 │
                 ▼ (Results collected)
    ┌─────────────────────────────────┐
    │ Analyze Results                 │
    │                                 │
    │ email_success?  transfer_success?│
    │ ✅              ✅              │
    │ ✅              ❌              │
    │ ❌              ✅              │
    │ ❌              ❌              │
    └────────────┬────────────────────┘
                 │
                 ▼
    ┌────────────────────────────────┐
    │ Show User Feedback              │
    │                                 │
    │ Success + Success:              │
    │ "✓ Success! Candidate moved."   │
    │                                 │
    │ Success + Failure:              │
    │ "⚠️ Email failed but data..."   │
    │                                 │
    │ Failure + Success:              │
    │ "⚠️ Email succeeded but..."     │
    │                                 │
    │ Failure + Failure:              │
    │ "❌ Error: [details]"            │
    └────────────┬────────────────────┘
                 │
                 ▼
    ┌────────────────────────────────┐
    │ Reload Tables                   │
    │ - loadApprovedCandidates()      │
    │ - loadSelectedCandidates()      │
    │                                 │
    │ Candidate should now appear in: │
    │ ✅ Selected table (not approved)│
    └────────────────────────────────┘
```

---

## Detailed Backend Flow

### Email Sending Path (Independent)

```
POST /admin/api/send-offer-email
{
  "email": "john@example.com",
  "name": "John Doe",
  "pdf_b64": "<BASE64_PDF>",
  "reference_number": "SZS_OFFER_2025_JAN_001"
}
        │
        ▼
    ┌─────────────────────────────────┐
    │ send_offer_email_endpoint()     │
    └─────────────────────────────────┘
        │
        ├─ Validate input parameters
        │
        ├─ Decode base64 PDF
        │
        ├─ Call send_offer_letter_email()
        │  └─ Sends email with PDF attachment
        │  └─ Returns True or False
        │
        ├─ Log result
        │
        └─ Return response
           │
           ├─ On Success:
           │  {
           │    "success": true,
           │    "message": "Offer letter email sent successfully"
           │  }
           │
           └─ On Error:
              {
                "success": false,
                "error": "Email send failed: SMTP timeout"
              }
              
        NOTE: Database is NOT modified
        NOTE: Errors are logged but don't stop workflow
```

### Data Transfer Path (Critical)

```
POST /admin/api/transfer-to-selected
{
  "usn": "CS21001",
  "candidate_id": 12345,
  "name": "John Doe",
  "email": "john@example.com",
  "domain": "FULL STACK DEVELOPER",
  "college": "XYZ College",
  "duration_months": 1,
  "pdf_b64": "<BASE64_PDF>",
  "reference_number": "SZS_OFFER_2025_JAN_001",
  "mode_of_internship": "free"
}
        │
        ▼
    ┌────────────────────────────────────┐
    │ transfer_to_selected_endpoint()    │
    └────────────────────────────────────┘
        │
        ├─ Validate input
        │
        ├─ Decode PDF from base64
        │
        ├─ Step 1: Find approved_candidate
        │  ├─ SELECT * FROM approved_candidates WHERE usn='CS21001'
        │  └─ If not found → ERROR
        │
        ├─ Step 2: Check if already in Selected
        │  ├─ SELECT * FROM Selected WHERE usn='CS21001'
        │  ├─ If found → Update existing record
        │  └─ If not → Create new record
        │
        ├─ Step 3: Generate candidate_id
        │  ├─ Format: SINYYDDsss (e.g., SIN25FD001)
        │  └─ Based on domain and year
        │
        ├─ Step 4: Populate Selected record
        │  ├─ INSERT/UPDATE into Selected table
        │  ├─ Store PDF in offer_letter_pdf column
        │  ├─ Store reference in offer_letter_reference
        │  ├─ Store timestamp in offer_letter_generated_date
        │  └─ COMMIT transaction
        │
        ├─ Step 5: Delete from approved_candidates
        │  ├─ DELETE FROM approved_candidates WHERE usn='CS21001'
        │  ├─ This is the TRANSFER (not just copy)
        │  └─ COMMIT transaction
        │
        └─ Return response
           │
           ├─ On Success:
           │  {
           │    "success": true,
           │    "message": "Successfully transferred...",
           │    "selected_candidate_id": "SIN25FD001"
           │  }
           │
           └─ On Error:
              {
                "success": false,
                "error": "Failed to transfer: [specific reason]"
              }
              
        NOTE: ALL database operations are included
        NOTE: Either all succeed or all fail (transaction safe)
```

---

## Database State Changes

### Initial State (Before Confirm & Send)

```
approved_candidates table:
┌──────┬─────────┬───────┬──────────┐
│ usn  │ name    │ email │ domain   │
├──────┼─────────┼───────┼──────────┤
│CS21  │ John    │john@… │ FULL     │
│001   │ Doe     │…      │ STACK    │
└──────┴─────────┴───────┴──────────┘

Selected table:
┌──────┬──────────┬──────────┐
│ usn  │ name     │ domain   │
├──────┼──────────┼──────────┤
│CS…   │ Jane…    │ AI       │
└──────┴──────────┴──────────┘
(CS21001 NOT HERE)
```

### Intermediate State (After Email Step)

```
(No database changes from email step)

approved_candidates table:
┌──────┬─────────┬───────┬──────────┐
│ usn  │ name    │ email │ domain   │
├──────┼─────────┼───────┼──────────┤
│CS21  │ John    │john@… │ FULL     │
│001   │ Doe     │…      │ STACK    │
└──────┴─────────┴───────┴──────────┘
(Still here - no changes)

Selected table:
(Unchanged)
```

### Final State (After Transfer Step)

```
approved_candidates table:
┌──────┬─────────┬───────┬──────────┐
│ usn  │ name    │ email │ domain   │
├──────┼─────────┼───────┼──────────┤
│      │         │       │          │
│(EMPTY)
└──────┴─────────┴───────┴──────────┘
(CS21001 DELETED - TRANSFERRED)

Selected table:
┌──────┬─────────┬──────────┬──────────┬────────────┬─────────────────┐
│ usn  │ name    │ domain   │ cand_id  │ offer_ref  │ offer_pdf       │
├──────┼─────────┼──────────┼──────────┼────────────┼─────────────────┤
│CS…   │ Jane…   │ AI       │ SIN25AI… │ SZS_OFFER… │ <PDF_bytes>     │
│CS21  │ John    │ FULL     │ SIN25FD  │ SZS_OFFER… │ <PDF_bytes>     │
│001   │ Doe     │ STACK    │ 001      │ 2025_JAN…  │ NEW ENTRY!      │
└──────┴─────────┴──────────┴──────────┴────────────┴─────────────────┘
(CS21001 NOW HERE with all offer letter data)
```

---

## Error Scenarios

### Scenario 1: Email Service Down ⚠️

```
Step 1: Send Email
    │
    └─ SMTP Connection Failed ❌
       Log: "Email send failed: Connection timeout"
       Response: {success: false, error: "..."}
       DB Change: None
       Continue: YES ✓
       │
       ▼
Step 2: Transfer Data
    │
    └─ SUCCESS ✅
       Response: {success: true, selected_candidate_id: "..."}
       DB Change: approved_candidates → Selected
       User Sees: "⚠️ Email failed but candidate moved to Selected"
       Result: DATA SAFE ✓
```

### Scenario 2: Database Connection Error ❌

```
Step 1: Send Email
    │
    └─ SUCCESS ✅
       Response: {success: true}
       DB Change: None (email only)
       Continue: YES ✓
       │
       ▼
Step 2: Transfer Data
    │
    └─ Database Connection Error ❌
       Error: "Could not connect to database"
       Response: {success: false, error: "..."}
       DB Change: NONE (transaction rolled back)
       User Sees: "❌ Error: Failed to transfer..."
       Result: DATA STUCK ❌ (candidate still in approved_candidates)
       Action: User must retry or contact admin
```

### Scenario 3: Both Success ✅✅

```
Step 1: Send Email
    │
    └─ SUCCESS ✅
       Response: {success: true}
       DB Change: None
       Continue: YES ✓
       │
       ▼
Step 2: Transfer Data
    │
    └─ SUCCESS ✅
       Response: {success: true, selected_candidate_id: "SIN25FD001"}
       DB Change: approved_candidates → Selected (complete transfer)
       User Sees: "✓ Success! Candidate moved to Selected"
       Result: PERFECT ✅
```

---

## Key Decision Points

```
User clicks "Confirm & Send"
        │
        ├─ Email independent?
        │  └─ YES → Continue on failure
        │
        ├─ Transfer data first or email first?
        │  └─ EMAIL FIRST → Preserve if it fails
        │
        ├─ If email fails, proceed with transfer?
        │  └─ YES → Critical for data safety
        │
        ├─ Delete from approved_candidates immediately?
        │  └─ YES → True transfer, not copy
        │
        └─ Show detailed error messages to user?
           └─ YES → Help admin troubleshoot
```

---

## Summary Table

| Component | Responsibility | Failure Impact | Recovery |
|-----------|-----------------|-----------------|----------|
| Email endpoint | Send offer PDF | Candidate not emailed | Manual resend later |
| Transfer endpoint | Move to Selected | Candidate stuck | Retry operation |
| PDF generation | Create PDF | No offer sent | Regenerate |
| DB transaction | Atomicity | Partial updates | Rollback + retry |
| Error logging | Record issues | Hard to debug | Check server logs |

---

## File References

- **Backend**: `admin_app.py` lines 4011-4252
- **Frontend**: `templates/admin_approved_candidates.html` lines 1014-1108
- **Documentation**: See `OFFER_LETTER_WORKFLOW.md` for details

