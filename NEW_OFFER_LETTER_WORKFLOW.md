# New Offer Letter Workflow Implementation

## Overview

The offer letter generation workflow has been redesigned to occur **after the admin accepts a candidate and chooses/confirms the domain**. The system now displays the generated offer letter for review before sending it to the candidate and transferring their data to the Selected table.

## Workflow Steps

### For Approved Candidates (admin_approved_candidates.html)

1. **Admin clicks Accept button** on a candidate row

   - Domain Change Modal opens
   - Shows current domain
   - Allows admin to select a different domain or keep current

2. **Admin confirms domain choice**

   - Calls `confirmAcceptWithDomain()`
   - Domain modal closes

3. **System generates offer letter**

   - Calls new endpoint: `POST /admin/api/generate-offer-letter-preview`
   - Parameters:
     - `candidate_id`: approved candidate ID
     - `source`: "approved"
     - `name`, `usn`, `college`, `email`: candidate data
     - `domain`: final domain choice (with or without changes)
     - `mode_of_internship`: "free" (for approved candidates)
     - `internship_type`: "free"
     - `duration`: "1 month"
   - Returns: base64-encoded PDF, reference number, filename

4. **Offer Letter Preview Modal displays**

   - Shows the generated PDF in an iframe
   - Has **Confirm & Send** button
   - Has **Cancel** button

5. **Admin reviews and confirms**
   - Calls `confirmOfferLetter()`
   - Calls new endpoint: `POST /admin/api/confirm-offer-letter`
   - Endpoint performs:
     - Sends email with offer letter attachment
     - Stores offer letter PDF in Selected table
     - Generates unique `candidate_id` for Selected table
     - Transfers all candidate data from `approved_candidates` to `Selected`
     - Deletes from `approved_candidates` table
   - Shows success message
   - Reloads candidates list

### For Paid Internships (admin_dashboard.js)

1. **Admin clicks Accept button** on a paid internship applicant

   - Calls `updateStatus()` with status="ACCEPTED" and internshipType="paid"
   - New logic routes to `initiatePaidInternshipAccept()`

2. **System fetches applicant data**

   - Retrieves all fields from paid_internship_application table
   - Stores in `currentPaidInternshipData`

3. **System generates offer letter**

   - Similar to approved candidates flow
   - Calls `POST /admin/api/generate-offer-letter-preview`
   - Parameters:
     - `source`: "paid"
     - `candidate_id`: application_id from paid_internship table
     - `domain`: domain from paid application
     - `mode_of_internship`: "paid"
     - `internship_type`: "paid"
     - `duration`: "3 months"

4. **Offer Letter Preview Modal displays**

   - Shows PDF in iframe
   - **Confirm & Send** button
   - **Cancel** button

5. **Admin confirms**
   - Calls `confirmOfferLetter()`
   - Calls `POST /admin/api/confirm-offer-letter`
   - Endpoint performs:
     - Sends email with offer letter
     - Stores offer letter in Selected table
     - Transfers data from `paid_internship_application` to `Selected`
     - Deletes from `paid_internship_application` and `paid_document_store`

## New Backend Endpoints

### 1. `POST /admin/api/generate-offer-letter-preview`

**Purpose**: Generate offer letter PDF and return as base64

**Input**:

```json
{
  "candidate_id": <id>,
  "source": "approved" | "paid",
  "name": <name>,
  "usn": <usn>,
  "college": <college>,
  "email": <email>,
  "domain": <domain>,
  "mode_of_internship": <mode>,
  "internship_type": "free" | "paid",
  "duration": <duration_str>
}
```

**Output**:

```json
{
  "success": true,
  "pdf_data": "<base64_encoded_pdf>",
  "reference_number": "<ref_no>",
  "filename": "<filename>"
}
```

### 2. `POST /admin/api/confirm-offer-letter`

**Purpose**: Send email, store offer letter in DB, transfer candidate data

**Input**:

```json
{
  "candidate_id": <id>,
  "source": "approved" | "paid",
  "name": <name>,
  "usn": <usn>,
  "email": <email>,
  "domain": <domain>,
  "college": <college>,
  "mode_of_internship": <mode>,
  "internship_type": "free" | "paid",
  "duration": <duration_in_months>,
  "pdf_b64": "<base64_pdf>",
  "reference_number": "<ref_no>"
}
```

**Output**:

```json
{
  "success": true,
  "message": "Offer letter confirmed, email sent, and candidate transferred to Selected",
  "candidate_id": "<newly_generated_candidate_id>",
  "email_sent": true
}
```

## Data Flow

### Approved Candidates

```
approved_candidates table
  ↓
(Admin accepts + domain choice)
  ↓
Generate offer letter PDF
  ↓
Display in modal
  ↓
Admin confirms
  ↓
Send email + Store PDF in Selected + Delete from approved_candidates
  ↓
Selected table (with offer_letter_pdf, offer_letter_reference)
```

### Paid Internships

```
paid_internship_application table
  ↓
(Admin accepts)
  ↓
Generate offer letter PDF
  ↓
Display in modal
  ↓
Admin confirms
  ↓
Send email + Store PDF in Selected + Delete from paid tables
  ↓
Selected table (with offer_letter_pdf, offer_letter_reference)
```

## Key Data Stored in Selected Table

- `usn`: Unique student number
- `name`, `email`, `college`: Basic info
- `domain`: Domain (with or without admin changes)
- `roles`: "{domain} Intern"
- `offer_letter_pdf`: LONGBLOB (binary PDF)
- `offer_letter_reference`: Reference number (e.g., "SZS/OFFR/2025/NOV/001")
- `offer_letter_generated_date`: Timestamp
- `internship_duration`: "1 month", "3 months", etc.
- `mode_of_internship`: "free", "paid", "remote-based opportunity", etc.

## File Changes

### Backend

- **admin_app.py**: Added two new endpoints:
  - `generate_offer_letter_preview()`: Lines ~3633-3710
  - `confirm_offer_letter()`: Lines ~3713-3870

### Frontend - Approved Candidates

- **admin_approved_candidates.html**:
  - Added Offer Letter Modal (after Certificate Modal)
  - Updated JavaScript in `confirmAcceptWithDomain()` to trigger offer letter flow
  - Added functions: `generateAndShowOfferLetter()`, `showOfferLetterModal()`, `closeOfferLetterModal()`, `confirmOfferLetter()`

### Frontend - Dashboard

- **admin_dashboard.html**: Added Offer Letter Modal
- **admin_dashboard.js**:
  - Updated `updateStatus()` to route paid internships to new flow
  - Added functions: `initiatePaidInternshipAccept()`, `generateAndShowOfferLetterForPaid()`, `closeOfferLetterModal()`, `confirmOfferLetter()`

## Testing Checklist

- [ ] Approved candidate accept flow:

  - [ ] Click Accept button
  - [ ] Domain modal appears
  - [ ] Change or keep domain
  - [ ] Offer letter displays correctly
  - [ ] Click Confirm & Send
  - [ ] Email received
  - [ ] Candidate moved to Selected table
  - [ ] Candidate removed from approved_candidates table

- [ ] Paid internship accept flow:

  - [ ] Click Accept on paid applicant
  - [ ] Offer letter generates and displays
  - [ ] Click Confirm & Send
  - [ ] Email received
  - [ ] Applicant moved to Selected table
  - [ ] Applicant removed from paid_internship_application table

- [ ] Edge cases:
  - [ ] Cancel offer letter confirmation (modal closes, no data transferred)
  - [ ] Duplicate USN handling (if candidate already in Selected)
  - [ ] Email sending with PDF attachment
  - [ ] Offer letter reference number generation

## Notes

- Role is automatically set as "{domain} Intern" during acceptance
- Default internship duration is "1 month" for free internships, "3 months" for paid
- Email is sent with the offer letter PDF as an attachment using the existing `send_offer_letter_email()` function
- Offer letter PDF is stored in the database for future retrieval
- All USN values are validated and checked for duplicates before transfer
