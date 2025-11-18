# VISUAL SUMMARY: Internship Mode Registration Data

## 🎯 One-Page Quick Reference

### WHERE IS INTERNSHIP MODE?

```
┌─────────────────────────────────────────────────────┐
│           SELECTED TABLE ✅                          │
│                                                       │
│  ┌──────────────────────────────────────────────┐  │
│  │ mode_of_internship: VARCHAR                  │  │
│  │ Values: free | paid | remote-based |         │  │
│  │         hybrid-based | on-site-based         │  │
│  └──────────────────────────────────────────────┘  │
│                   PRIMARY STORAGE                    │
│                   LOCATION                           │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│       APPROVED_CANDIDATES TABLE ❌                   │
│                                                       │
│  ⚠️  NO internship_mode FIELD (DATA GAP)             │
│  Only has: mode_of_interview (online/offline)      │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│   FREE/PAID_INTERNSHIP TABLES ❌ (IMPLICIT)         │
│                                                       │
│  ❌ No explicit mode_of_internship field            │
│  Mode is implicit from table name:                 │
│     • free_internship → implicitly "free"          │
│     • paid_internship → implicitly "paid"          │
└─────────────────────────────────────────────────────┘
```

---

## 📊 TABLE COMPARISON

```
┌─────────────────────────────────────────────────────────────────┐
│                     REGISTRATION DATA STORAGE                    │
├──────────────┬─────────┬──────────────┬──────────┬──────────────┤
│ Table        │ USN     │ Intern Mode  │ Profile  │ Files/BLOBs  │
├──────────────┼─────────┼──────────────┼──────────┼──────────────┤
│ free_        │ ✅      │ ❌ implicit  │ ✅       │ ✅ BLOBs     │
│ internship   │         │              │          │              │
├──────────────┼─────────┼──────────────┼──────────┼──────────────┤
│ paid_        │ ✅      │ ❌ implicit  │ ✅       │ ✅ BLOBs     │
│ internship   │         │              │          │              │
├──────────────┼─────────┼──────────────┼──────────┼──────────────┤
│ approved_    │ ✅ (PK) │ ❌ MISSING   │ ✅       │ ✅ BLOBs     │
│ candidates   │         │  (DATA GAP)  │          │              │
├──────────────┼─────────┼──────────────┼──────────┼──────────────┤
│ Selected     │ ✅ (PK) │ ✅ EXPLICIT  │ ✅       │ ✅ offer PDF │
│              │         │ mode_of_     │          │              │
│              │         │ internship   │          │              │
└──────────────┴─────────┴──────────────┴──────────┴──────────────┘
```

---

## 🔄 DATA FLOW: Registration → Selection

### Path 1: FREE INTERNSHIP

```
┌─────────────────────────────────────┐
│   free_internship Table             │
│   id, name, usn, email, phone...    │
│   resume, project, id_proof (BLOBs) │
│   MODE: ❌ Implicit "free"           │
└──────────────┬──────────────────────┘
               │ ADMIN CLICKS ACCEPT
               ▼
┌─────────────────────────────────────┐
│   approved_candidates Table         │
│   usn, application_id, name, email..│
│   mode_of_interview='online'        │
│   resume_content, project_content   │
│   MODE: ❌ NOT STORED (GAP!)        │
└──────────────┬──────────────────────┘
               │ ADMIN CLICKS ACCEPT
               ▼
┌─────────────────────────────────────┐
│   Selected Table                    │
│   usn, name, email, candidate_id    │
│   ✅ mode_of_internship='free'      │
│   status='ongoing'                  │
│   completion_date = today + 1 month │
└─────────────────────────────────────┘
```

### Path 2: PAID INTERNSHIP

```
┌─────────────────────────────────────┐
│   paid_internship Table             │
│   id, name, usn, email, phone...    │
│   project_description, duration     │
│   resume, project (BLOBs)           │
│   MODE: ❌ Implicit "paid"          │
└──────────────┬──────────────────────┘
               │ ADMIN CLICKS ACCEPT
               │ (BYPASSES approved_candidates)
               ▼
┌─────────────────────────────────────┐
│   Selected Table                    │
│   candidate_id, name, email...      │
│   ✅ mode_of_internship='paid'      │
│   status='ongoing'                  │
│   completion_date = today + 3 months│
│   offer_letter_pdf (auto-generated) │
└─────────────────────────────────────┘
```

---

## 🔍 FIELD MAPPING

```
USER REGISTRATION INPUT
    │
    ├─ name ──────────────────► Selected.name ✅
    ├─ email ─────────────────► Selected.email ✅
    ├─ phone ─────────────────► Selected.phone ✅
    ├─ usn ───────────────────► Selected.usn ✅ (PRIMARY KEY)
    ├─ year ──────────────────► Selected.year ✅
    ├─ qualification ─────────► Selected.qualification ✅
    ├─ branch ────────────────► Selected.branch ✅
    ├─ college ───────────────► Selected.college ✅
    ├─ domain ────────────────► Selected.domain ✅
    │
    ├─ Table name ────────────► mode_of_internship = ? ⚠️
    │                             (implicit, not explicit)
    │
    ├─ Resume file ───────────► Selected.resume_content ✅
    ├─ Project file ──────────► Selected.internship_project_content ✅
    ├─ ID Proof file ─────────► approved_candidates.id_proof_content ✅
    │
    └─ Interview type ────────► approved_candidates.mode_of_interview ✅
                                (Different from internship_mode!)
```

---

## 💾 SQL OPERATIONS

### INSERT (When accepting)

```sql
INSERT INTO Selected (
    name, email, phone, usn, year, qualification, branch, college, domain,
    roles, candidate_id, ✅ mode_of_internship, status, approved_date, completion_date
)
VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s, %s,
    %s, %s, ✅ 'free' or 'paid', 'ongoing', CURDATE(), DATE_ADD(CURDATE(), INTERVAL X MONTH)
)
```

### SELECT (When viewing)

```sql
SELECT usn, name, domain, ✅ mode_of_internship, status
FROM Selected
WHERE usn = %s
```

### UPDATE (If changing later)

```sql
UPDATE Selected SET
    ✅ mode_of_internship = %s
WHERE usn = %s
```

---

## 📱 API ENDPOINTS

```
GET /admin/api/get-selected
  └─ Returns: ALL Selected records with ✅ mode_of_internship

GET /admin/api/get-selected-candidate/<id>
  └─ Returns: Single record with ✅ mode_of_internship

GET /admin/api/get-completed-candidates
  └─ Returns: Completed records with ✅ mode_of_internship

POST /accept/<user_id>?type=free|paid
  └─ Sets: ✅ mode_of_internship based on ?type parameter
```

---

## ⏱️ TIMELINE: When Is Mode Set?

```
Timeline of Data Entry for Internship Mode:

User Registration (t=0)
│
├─ free_internship table created
│ └─ mode: ❌ NOT STORED (implicit from table name)
│
├─ Time passes...
│
└─ Admin Accepts (t=X)
   │
   ├─ If FREE internship:
   │ ├─ Move to approved_candidates
   │ │ └─ mode: ❌ STILL NOT STORED (data gap!)
   │ │
   │ └─ Move to Selected
   │    └─ mode: ✅ NOW STORED as mode_of_internship='free'
   │
   └─ If PAID internship:
     └─ Move directly to Selected (skip approved_candidates)
        └─ mode: ✅ STORED as mode_of_internship='paid'

Result in Selected table:
  mode_of_internship is NOW EXPLICIT and QUERYABLE ✅
```

---

## 🎯 INTERNSHIP MODE VALUES

```
┌──────────────────────┬─────────────┬──────────────────┐
│ Value                │ Duration    │ Storage Location │
├──────────────────────┼─────────────┼──────────────────┤
│ "free"               │ 1 month     │ Selected table   │
│ "paid"               │ 3 months    │ Selected table   │
│ "remote-based        │ 3 months    │ Selected table   │
│  opportunity"        │             │ (if set via API) │
│ "hybrid-based        │ 3 months    │ Selected table   │
│  opportunity"        │             │ (if set via API) │
│ "on-site based       │ 3 months    │ Selected table   │
│  opportunity"        │             │ (if set via API) │
└──────────────────────┴─────────────┴──────────────────┘
```

---

## 🚨 IMPORTANT DISTINCTIONS

### ⚠️ DON'T CONFUSE THESE:

```
mode_of_interview  ≠  mode_of_internship

MODE_OF_INTERVIEW                MODE_OF_INTERNSHIP
├─ What: Interview format        ├─ What: Internship type
├─ Values: online, offline       ├─ Values: free, paid, remote, hybrid, on-site
├─ Table: approved_candidates    ├─ Table: Selected
├─ Field: mode_of_interview      ├─ Field: mode_of_internship
├─ Purpose: How interview        ├─ Purpose: Type of internship
│          is conducted          │              assigned
└─ Set by: Selection dropdown    └─ Set by: Accept flow (free/paid)
```

---

## 📋 CODE LOCATIONS

```
admin_app.py
├─ Line 1317-1341: UPDATE with mode_of_internship
├─ Line 1358-1367: INSERT with mode_of_internship
├─ Line 1663-1850: admin_accept() main function
├─ Line 1702-1715: Check duplicate before accepting
├─ Line 1772-1777: INSERT for paid (mode='paid')
├─ Line 3577: SELECT with mode_of_internship
└─ Line 3605: Extract mode_of_internship value

models.py
├─ ApprovedCandidate class
└─ ⚠️ Has mode_of_interview but NOT internship_mode (gap)

fix_selected_usn_pk.py
├─ CREATE TABLE Selected
└─ ✅ Contains mode_of_internship definition

templates/admin_approved_candidates.html
├─ Line 527-528: Internship type dropdown selector
└─ Shows: remote-based, on-site, hybrid options
```

---

## ✅ CHECKLIST: What's Available

### Registration Data Available ✅

- [x] Name
- [x] Email
- [x] Phone
- [x] USN (Unique Student Number)
- [x] Year
- [x] Qualification
- [x] Branch
- [x] College
- [x] Domain/Specialization
- [x] Resume file
- [x] Project document
- [x] ID proof

### Internship Mode Data

- [x] Stored in Selected table
- [x] Values: free, paid, remote-based, hybrid-based, on-site-based
- [x] Queryable via SQL
- [x] Available via API endpoints
- [x] Duration calculated from mode
- [x] Candidate ID generated (SIN25FD001)
- [ ] ❌ NOT in approved_candidates table (gap)

### Related Fields

- [x] mode_of_interview (online/offline - different field!)
- [x] Interview slot date/time (from slot_booking table)
- [x] Generated offer letter (for paid)
- [x] Completion date (calculated from mode)
- [x] Status (ongoing/completed)

---

## 🎓 QUICK START GUIDE

### "I want to find where internship mode is used"

1. Open: **INTERNSHIP_MODE_QUICK_REFERENCE.md** (Line numbers section)
2. Go to: admin_app.py line 1317-1850
3. Search for: "mode_of_internship"

### "I want to query internship mode"

1. Open: **INTERNSHIP_MODE_QUICK_REFERENCE.md** (SQL Examples section)
2. Use: `SELECT mode_of_internship FROM Selected WHERE usn = ?`
3. Join with: approved_candidates or free/paid_internship as needed

### "I want to add it to approved_candidates"

1. Open: **DATABASE_SCHEMA_MODE_STORAGE.md** (Section 5)
2. Run: Provided ALTER TABLE statement
3. Update: models.py to add field
4. Deploy: Changes to admin_app.py

### "I want to understand the full system"

1. Read: **INTERNSHIP_MODE_REGISTRATION_ANALYSIS.md** (sections 1-5)
2. Reference: **DATABASE_SCHEMA_MODE_STORAGE.md** (technical details)
3. Use: **INTERNSHIP_MODE_QUICK_REFERENCE.md** (for quick lookups)

---

## 📌 KEY TAKEAWAYS

```
1. ✅ Internship mode IS tracked in Selected.mode_of_internship
2. ❌ It's NOT stored in approved_candidates (data gap)
3. 📊 Values: free, paid, remote-based, hybrid-based, on-site-based
4. 🔄 Duration: 1 month for free, 3 months for others
5. 📍 Primary location: Selected table
6. ⚠️  Different from mode_of_interview (interview format)
7. 📡 Available via API: /admin/api/get-selected, etc.
8. 🔍 Queryable: SELECT mode_of_internship FROM Selected
9. 🛠️ Recommended fix: Add column to approved_candidates
10. 📝 All details in provided documentation
```

---

End of Visual Summary
See individual documentation files for complete details.
