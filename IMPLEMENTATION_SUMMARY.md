# Implementation Complete: New Offer Letter Workflow

## Summary of Changes

### ✓ Backend API Endpoints (admin_app.py)

**1. POST /admin/api/generate-offer-letter-preview**

- Generates offer letter PDF after domain selection
- Returns base64-encoded PDF for in-browser display
- Extracts candidate data: name, USN, college, email, domain
- Creates role as "{domain} Intern"
- Generates unique reference number

**2. POST /admin/api/confirm-offer-letter**

- Sends email with offer letter attachment
- Stores offer letter PDF and reference in Selected table
- Transfers candidate data from source table to Selected
- Deletes from source table (approved_candidates or paid_internship_application)
- Returns newly generated candidate_id

### ✓ Frontend - Approved Candidates (admin_approved_candidates.html)

**Workflow:**

1. Admin clicks Accept → Domain modal shows
2. Admin selects/keeps domain → Offer Letter Preview modal shows PDF
3. Admin clicks "Confirm & Send" → Email sent, data transferred to Selected

**New Components:**

- Offer Letter Modal with PDF viewer
- Updated JavaScript functions for offer letter generation and confirmation

### ✓ Frontend - Dashboard (admin_dashboard.html + admin_dashboard.js)

**Workflow:**

1. Admin clicks Accept on paid internship → Offer letter generates
2. Offer Letter Preview modal shows PDF
3. Admin clicks "Confirm & Send" → Email sent, data transferred to Selected

**Key Changes:**

- `updateStatus()` now routes paid internship accepts to new workflow
- `initiatePaidInternshipAccept()` fetches applicant data
- `generateAndShowOfferLetterForPaid()` calls new API endpoint
- `confirmOfferLetter()` finalizes the workflow

## Process Flow

### Approved Candidates Path

```
Accept Button
    ↓
Domain Change Modal
    ↓ (confirm domain)
Generate Offer Letter (API call)
    ↓
Offer Letter Preview Modal (show PDF)
    ↓ (confirm)
Send Email + Transfer Data (API call)
    ↓
Candidate moved to Selected table ✓
```

### Paid Internship Path

```
Accept Button (paid internship)
    ↓
Fetch Applicant Data
    ↓
Generate Offer Letter (API call)
    ↓
Offer Letter Preview Modal (show PDF)
    ↓ (confirm)
Send Email + Transfer Data (API call)
    ↓
Applicant moved to Selected table ✓
```

## Data Stored in Selected Table

When offer letter is confirmed:

- **offer_letter_pdf**: Binary PDF file (LONGBLOB)
- **offer_letter_reference**: Unique reference like "SZS/OFFR/2025/NOV/001"
- **offer_letter_generated_date**: Timestamp of generation
- **candidate_id**: Auto-generated unique ID (e.g., "SIN25FD001")
- **roles**: "{domain} Intern"
- **domain**: Final domain after any admin changes

## Email Flow

The `send_offer_letter_email()` function is called with:

- Recipient email
- Recipient name
- PDF bytes (from generated offer letter)
- Reference number

Email is sent with PDF attached as an attachment.

## Error Handling

- **Duplicate USN**: Checked before transfer, returns 409 error
- **Missing data**: Validates all required fields before processing
- **PDF generation fails**: Shows error in modal, allows retry
- **Email send fails**: Still completes data transfer, logs warning
- **Database errors**: Caught and reported to admin

## Key Features

✓ **Centralized offer letter generation** - Uses existing `generate_offer_pdf()` function
✓ **In-browser preview** - PDF displayed in iframe before sending
✓ **Domain flexibility** - Admins can change domain for approved candidates
✓ **Atomic operations** - Email + data transfer happen together
✓ **Audit trail** - Reference number and generation date stored
✓ **Email attachment** - Offer letter sent as PDF attachment
✓ **Batch-friendly** - Can process multiple acceptances in sequence
✓ **Handles both workflows** - Free (approved) and paid internships

## No Breaking Changes

- Old accept workflow still works for free internships (if not from approved_candidates)
- Existing Selected table structure unchanged (only added offer letter fields)
- Email templates unchanged
- PDF generation logic unchanged
- All existing endpoints functional
