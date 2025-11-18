# Internship Mode Registration Data - Comprehensive Analysis

## Executive Summary

The application stores user/internship registration data across multiple tables, with internship mode/type information being tracked in the `Selected` table via the `mode_of_internship` field. This field stores the type of internship (e.g., "free", "paid", "remote-based opportunity", "hybrid-based opportunity", "on-site based opportunity").

---

## 1. TABLE STRUCTURES & RELEVANT FIELDS

### 1.1 Primary Registration Tables

#### **free_internship / free_internship_application**

- **Table Name**: `free_internship` or `free_internship_application` (name varies)
- **Primary Key**: `id` (INT AUTO_INCREMENT)
- **Relevant Columns for Registration**:
  - `id`: Application ID
  - `name`: Applicant name
  - `usn`: Unique Student Number (unique constraint)
  - `email`: Email address
  - `phone`: Phone number
  - `year`: Academic year
  - `qualification`: Educational qualification
  - `branch`: Department/branch
  - `college`: College name
  - `domain`: Domain/specialization
  - `resume`: LONGBLOB (resume file)
  - `project_document`: Project document BLOB
  - `id_proof`: ID proof BLOB
  - `created_at`: Timestamp

**Note**: This table does NOT have a field for "internship mode" - it's implicitly "free"

#### **paid_internship / paid_internship_application**

- **Table Name**: `paid_internship` or `paid_internship_application`
- **Primary Key**: `id` (INT AUTO_INCREMENT)
- **Relevant Columns for Registration**:
  - Same as free_internship (id, name, usn, email, phone, year, qualification, branch, college, domain, resume, project, id_proof, created_at)
  - Additional fields may include: `project_description`, `project_title`, `internship_duration`

**Note**: This table does NOT have a field for "internship mode" - it's implicitly "paid"

#### **approved_candidates** (SQLAlchemy ORM Model)

- **Table Name**: `approved_candidates`
- **Primary Key**: `usn` (VARCHAR(50))
- **File**: `c:\Users\admin\swizosoft\models.py`
- **Relevant Columns for Registration**:
  - `usn`: Primary key (Unique Student Number)
  - `application_id`: VARCHAR(20), UNIQUE
  - `user_id`: INT, UNIQUE (from free_internship.id)
  - `name`: VARCHAR(100)
  - `email`: VARCHAR(100)
  - `phone_number`: VARCHAR(15)
  - `year`: VARCHAR(20)
  - `qualification`: VARCHAR(50)
  - `branch`: VARCHAR(100)
  - `college`: VARCHAR(200)
  - `domain`: VARCHAR(100)
  - `mode_of_interview`: VARCHAR(20), default='online' ⚠️ (NOTE: This is interview mode, NOT internship mode)
  - `resume_name`: VARCHAR(255)
  - `resume_content`: MEDIUMBLOB
  - `project_document_name`: VARCHAR(255)
  - `project_document_content`: MEDIUMBLOB
  - `id_proof_name`: VARCHAR(255)
  - `id_proof_content`: MEDIUMBLOB
  - `job_description`: TEXT (cached snapshot)
  - `created_at`: DATETIME
  - `updated_at`: DATETIME

**CRITICAL**: The `approved_candidates` table does NOT currently have a field to store internship mode information!

#### **Selected** (Main Candidates Table)

- **Table Name**: `Selected`
- **Primary Key**: `usn` (VARCHAR(20))
- **Unique Constraints**: `application_id` (VARCHAR(20))
- **File**: Table defined in `fix_selected_usn_pk.py`
- **Columns with internship mode**:
  - `id`: INT UNIQUE AUTO_INCREMENT
  - `application_id`: VARCHAR(20) UNIQUE
  - `name`: VARCHAR(100)
  - `email`: VARCHAR(100)
  - `phone`: VARCHAR(15)
  - `usn`: VARCHAR(20) PRIMARY KEY
  - `year`: VARCHAR(50)
  - `qualification`: VARCHAR(50)
  - `branch`: VARCHAR(100)
  - `college`: VARCHAR(200)
  - `domain`: VARCHAR(100)
  - `roles`: VARCHAR (e.g., "Full Stack Developer Intern")
  - `candidate_id`: VARCHAR (e.g., "SIN25FD001")
  - **`mode_of_internship`**: VARCHAR ✅ **THIS FIELD STORES INTERNSHIP MODE**
    - Possible values: "free", "paid", "remote-based opportunity", "hybrid-based opportunity", "on-site based opportunity"
  - `project_description`: VARCHAR(255)
  - `internship_project_name`: VARCHAR(255)
  - `internship_project_content`: MEDIUMBLOB
  - `project_title`: VARCHAR(50)
  - `approved_date`: DATE
  - `status`: ENUM('ongoing', 'completed')
  - `completion_date`: DATE
  - `resend_count`: INT
  - `created_at`: TIMESTAMP

---

## 2. FIELDS RELATED TO INTERNSHIP MODE

### Found Mode-Related Fields:

1. **`Selected.mode_of_internship`** ✅ PRIMARY FIELD

   - Location: `Selected` table
   - Type: VARCHAR
   - Values: "free", "paid", "remote-based opportunity", "hybrid-based opportunity", "on-site based opportunity"
   - Used to store the type/mode of internship when candidate is accepted

2. **`approved_candidates.mode_of_interview`** ⚠️ NOT INTERNSHIP MODE

   - Location: `approved_candidates` table
   - Type: VARCHAR(20)
   - Default: "online"
   - Values: "online", "offline" (this is interview mode, NOT internship mode)

3. **Implicit Mode** (from table name):
   - `free_internship` or `free_internship_application` → implicitly "free" mode
   - `paid_internship` or `paid_internship_application` → implicitly "paid" mode

---

## 3. SQL QUERIES THAT FETCH/UPDATE INTERNSHIP MODE DATA

### 3.1 Insert Internship Mode (From Free Internship Accept Flow)

**File**: `admin_app.py`, lines 1358-1367
**Location**: `handle_approved_candidate_accept()` function

```sql
INSERT INTO Selected
(name, email, phone, usn, year, qualification, branch, college, domain, roles,
 approved_date, status, completion_date, candidate_id, mode_of_internship)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURDATE(), 'ongoing',
        DATE_ADD(CURDATE(), INTERVAL %s MONTH), %s, %s)
```

- **Parameter 14** (last): `internship_type` variable (e.g., "free")

### 3.2 Insert Internship Mode (From Paid Internship Accept Flow)

**File**: `admin_app.py`, lines 1772-1777
**Location**: `admin_accept()` function

```sql
INSERT INTO Selected
(candidate_id, name, email, phone, usn, year, qualification, branch, college, domain, roles,
 project_description, internship_project_name, internship_project_content, project_title,
 approved_date, status, completion_date, resend_count, mode_of_internship)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURDATE(), %s,
        DATE_ADD(CURDATE(), INTERVAL %s MONTH), %s, %s)
```

- **Parameter 20** (last): `'paid'` (hardcoded for paid internship)

### 3.3 Update Internship Mode

**File**: `admin_app.py`, lines 1325-1341
**Location**: `handle_approved_candidate_accept()` function (UPDATE path)

```sql
UPDATE Selected SET
    name = %s,
    email = %s,
    phone = %s,
    year = %s,
    qualification = %s,
    branch = %s,
    college = %s,
    domain = %s,
    roles = %s,
    approved_date = CURDATE(),
    status = 'ongoing',
    completion_date = DATE_ADD(CURDATE(), INTERVAL %s MONTH),
    candidate_id = %s,
    mode_of_internship = %s
    WHERE usn = %s
```

- **Parameter 13**: `internship_type` (e.g., "free")

### 3.4 Fetch Internship Mode

**File**: `admin_app.py`, line 3577
**Location**: API endpoint (line 3577)

```sql
SELECT name, usn, email, college, domain, roles, candidate_id, mode_of_internship
FROM Selected [WHERE ...]
```

### 3.5 Fetch All Selected Records with Internship Mode

**File**: `admin_app.py`, line 502, 548
**Location**: `admin_api_get_selected()` and `admin_api_get_completed_candidates()`

```sql
SELECT * FROM `Selected` WHERE status = 'ongoing' ORDER BY approved_date DESC
SELECT * FROM `Selected` WHERE status = 'completed' ORDER BY completion_date DESC
```

- These return all columns including `mode_of_internship`

---

## 4. WHERE INTERNSHIP MODE DATA IS USED

### 4.1 Code File Locations

| File Path                     | Line(s)    | Function                             | Purpose                                                                  |
| ----------------------------- | ---------- | ------------------------------------ | ------------------------------------------------------------------------ |
| `admin_app.py`                | 1317-1341  | `handle_approved_candidate_accept()` | Set `mode_of_internship` when accepting approved candidate               |
| `admin_app.py`                | 1358-1367  | `handle_approved_candidate_accept()` | INSERT with `mode_of_internship`                                         |
| `admin_app.py`                | 1702-1715  | `admin_accept()`                     | Check duplicate USN in `Selected`                                        |
| `admin_app.py`                | 1772-1777  | `admin_accept()`                     | INSERT paid internship with `mode_of_internship='paid'`                  |
| `admin_app.py`                | 3577       | Certificate generation               | SELECT `mode_of_internship` for offer letter                             |
| `admin_app.py`                | 3605       | Certificate generation               | Use `mode_of_internship` to determine internship type                    |
| `static/js/admin_selected.js` | 67, 87, 99 | JavaScript frontend                  | Display "Interview Mode" (NOT internship mode, uses `mode_of_interview`) |

### 4.2 API Endpoints That Return Internship Mode

| Endpoint                                 | File         | Line | Method | Returns                                          |
| ---------------------------------------- | ------------ | ---- | ------ | ------------------------------------------------ |
| `/admin/api/get-selected`                | admin_app.py | 500  | GET    | All Selected records with `mode_of_internship`   |
| `/admin/api/get-completed-candidates`    | admin_app.py | 546  | GET    | Completed candidates with `mode_of_internship`   |
| `/admin/api/get-selected-candidate/<id>` | admin_app.py | 680  | GET    | Single Selected record with `mode_of_internship` |

---

## 5. REGISTRATION DATA FLOW

### 5.1 Free Internship Flow

```
1. User registers → free_internship table (no mode field, implicitly "free")
   ├─ ID, name, USN, email, phone, year, qualification, branch, college, domain
   └─ resume, project_document, id_proof (BLOBs in free_document_store)

2. Admin accepts → moved to approved_candidates table
   ├─ Extracts: name, email, phone, usn, year, qualification, branch, college, domain
   ├─ Stores: mode_of_interview = 'online' (interview mode, NOT internship mode)
   └─ Deleted from free_internship

3. Admin accepts approved candidate → moved to Selected table
   ├─ Includes: mode_of_internship = "free" (the actual internship mode!)
   ├─ Generated: candidate_id (SIN25FD001 format)
   └─ Sets: status = 'ongoing', completion_date = 1 month
```

### 5.2 Paid Internship Flow

```
1. User registers → paid_internship table (no mode field, implicitly "paid")
   ├─ ID, name, USN, email, phone, year, qualification, branch, college, domain
   ├─ project_description, internship_duration
   └─ resume, project (BLOBs in paid_document_store)

2. Admin accepts → directly moved to Selected table (BYPASSES approved_candidates)
   ├─ Includes: mode_of_internship = "paid"
   ├─ Generated: candidate_id (SIN25FD001 format)
   ├─ Sets: status = 'ongoing'
   └─ Completion_date based on internship_duration (default 3 months for paid)
```

---

## 6. APPROVED_CANDIDATES TABLE ISSUE ⚠️

### Current Status

- The `approved_candidates` table does **NOT** have a field to store internship mode
- It only has `mode_of_interview` (online/offline for interview)
- When moving to `Selected`, the `internship_type` is passed from the request, but not stored in `approved_candidates`

### What Fields ARE Stored

- `usn`, `application_id`, `user_id`, `name`, `email`, `phone_number`
- `year`, `qualification`, `branch`, `college`, `domain`
- `mode_of_interview` (⚠️ Interview mode, not internship mode)
- `resume_name`, `resume_content`, `project_document_name`, `project_document_content`
- `id_proof_name`, `id_proof_content`, `job_description`

### What's MISSING

- **`internship_mode` or `internship_type`** field to store the type of internship

---

## 7. RECOMMENDED SCHEMA MODIFICATION

To properly store internship mode in `approved_candidates` table, add:

```sql
ALTER TABLE approved_candidates
ADD COLUMN internship_mode VARCHAR(50) DEFAULT 'free'
AFTER mode_of_interview;
```

**Or in the models.py**:

```python
internship_mode = db.Column(db.String(50), default='free')  # NEW LINE
```

This would allow:

- Tracking whether a candidate was approved for free/paid/hybrid internship
- Better audit trail and reporting
- Easier data recovery if candidate data is modified

---

## 8. API ENDPOINTS THAT WORK WITH INTERNSHIP DATA

### Registration Data Fetch

- **`/admin/api/get-internships?type=free|paid`** - Fetch registrations
- **`/admin/api/get-selected`** - Fetch selected candidates (with `mode_of_internship`)
- **`/admin/api/get-completed-candidates`** - Fetch completed internships
- **`/admin/api/get-approved-candidates`** - Fetch approved candidates (before Selected)
- **`/admin/api/get-approved-candidate/<user_id>`** - Fetch single approved candidate

### Registration Data Management

- **`POST /accept/<user_id>`** - Accept and move to Selected (stores `mode_of_internship`)
- **`POST /reject/<user_id>`** - Reject application
- **`PUT /admin/api/edit-profile/<internship_id>`** - Edit profile fields
- **`GET /admin/api/get-profile/<internship_id>`** - Get profile before accepting

---

## 9. KEY FINDINGS SUMMARY

| Item                        | Status        | Details                                                                                                     |
| --------------------------- | ------------- | ----------------------------------------------------------------------------------------------------------- |
| **Internship Mode Storage** | ✅ EXISTS     | Stored in `Selected.mode_of_internship`                                                                     |
| **Field Types**             | VARCHAR       | Values: "free", "paid", "remote-based opportunity", "hybrid-based opportunity", "on-site based opportunity" |
| **In approved_candidates**  | ❌ MISSING    | Not stored - only `mode_of_interview` (interview mode)                                                      |
| **Registration Tables**     | ✅ EXIST      | `free_internship`, `paid_internship`                                                                        |
| **User Profile Data**       | ✅ COMPLETE   | name, email, phone, usn, year, qualification, branch, college, domain                                       |
| **SQL Queries**             | ✅ DOCUMENTED | INSERT/UPDATE/SELECT queries in admin_app.py                                                                |
| **API Endpoints**           | ✅ WORKING    | Multiple endpoints return internship mode data                                                              |

---

## 10. FILE REFERENCE GUIDE

| File                                       | Content                     | Relevant Lines                           |
| ------------------------------------------ | --------------------------- | ---------------------------------------- |
| `models.py`                                | ApprovedCandidate ORM model | 1-50 (entire file)                       |
| `admin_app.py`                             | Main application logic      | 1293-1380, 1663-1850, 3577-3605          |
| `fix_selected_usn_pk.py`                   | Selected table schema       | Entire file (CREATE TABLE definition)    |
| `create_approved_candidates_table.py`      | approved_candidates schema  | Entire file                              |
| `database_setup.sql`                       | Initial schema              | Entire file                              |
| `templates/admin_approved_candidates.html` | Frontend display            | Lines 527-528 (internship type dropdown) |

---

## 11. INTERNSHIP MODE VALUES REFERENCE

From the application code:

```python
# Possible internship_mode values:
"free"                          # Free internship
"paid"                          # Paid internship
"remote-based opportunity"      # Remote work
"hybrid-based opportunity"      # Hybrid (office + remote)
"on-site based opportunity"     # On-site only

# Duration mapping:
"free" → 1 month default
"paid" → 3 months default
"*-based opportunity" → 3 months default
```

---

## CONCLUSION

The application **successfully tracks internship mode/type** in the `Selected` table via the `mode_of_internship` field. This field is populated when candidates are accepted and contains values like "free", "paid", "remote-based opportunity", "hybrid-based opportunity", or "on-site based opportunity".

However, the `approved_candidates` table (intermediate stage) does **not store** this information, which could be improved by adding an `internship_mode` column for better data tracking and audit purposes.
