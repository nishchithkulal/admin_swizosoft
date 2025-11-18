# Database Schema: Internship Mode Storage

## 1. COMPLETE SELECTED TABLE SCHEMA

**File Reference**: `fix_selected_usn_pk.py`

```sql
CREATE TABLE Selected (
    id INT UNIQUE AUTO_INCREMENT,
    application_id VARCHAR(20) UNIQUE,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL,
    phone VARCHAR(15) NOT NULL,
    usn VARCHAR(20) NOT NULL PRIMARY KEY,
    year VARCHAR(50) NOT NULL,
    qualification VARCHAR(50) NOT NULL,
    branch VARCHAR(100) NOT NULL,
    college VARCHAR(200) NOT NULL,
    domain VARCHAR(100) NOT NULL,
    roles VARCHAR,
    candidate_id VARCHAR,

    -- INTERNSHIP MODE FIELD (✅ Main Storage Location)
    mode_of_internship VARCHAR DEFAULT 'free',

    -- Project Related Fields
    project_description VARCHAR(255),
    internship_project_name VARCHAR(255),
    internship_project_content MEDIUMBLOB,
    project_title VARCHAR(50),

    -- Status & Dates
    approved_date DATE NOT NULL DEFAULT CURDATE(),
    status ENUM('ongoing','completed') NOT NULL DEFAULT 'ongoing',
    completion_date DATE NOT NULL DEFAULT CURDATE(),
    resend_count INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Offer Letter Fields (auto-generated for paid internships)
    offer_letter_pdf MEDIUMBLOB,
    offer_letter_reference VARCHAR(50),
    offer_letter_generated_date DATETIME
) ENGINE=InnoDB
```

### Important Selected Fields

| Field Name           | Type                        | Default   | Purpose                 | Notes                     |
| -------------------- | --------------------------- | --------- | ----------------------- | ------------------------- |
| `usn`                | VARCHAR(20)                 | -         | PRIMARY KEY             | Unique Student Number     |
| `mode_of_internship` | VARCHAR                     | 'free'    | Internship type storage | **✅ PRIMARY MODE FIELD** |
| `candidate_id`       | VARCHAR                     | -         | Generated ID            | Format: SIN25FD001        |
| `status`             | ENUM('ongoing','completed') | 'ongoing' | Internship status       | -                         |
| `completion_date`    | DATE                        | -         | End date                | Calculated on insert      |
| `approved_date`      | DATE                        | -         | Start date              | Set to current date       |

---

## 2. APPROVED_CANDIDATES TABLE SCHEMA

**File Reference**: `models.py` and `create_approved_candidates_table.py`

```sql
CREATE TABLE approved_candidates (
    usn VARCHAR(50) PRIMARY KEY,
    application_id VARCHAR(20) UNIQUE NOT NULL,
    user_id INT UNIQUE,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL,
    phone_number VARCHAR(15) NOT NULL,

    -- Academic Information
    year VARCHAR(20) NOT NULL,
    qualification VARCHAR(50) NOT NULL,
    branch VARCHAR(100) NOT NULL,
    college VARCHAR(200) NOT NULL,
    domain VARCHAR(100) NOT NULL,

    -- Interview Mode (⚠️ NOT INTERNSHIP MODE)
    mode_of_interview VARCHAR(20) DEFAULT 'online',

    -- File Information
    resume_name VARCHAR(255),
    resume_content MEDIUMBLOB,
    project_document_name VARCHAR(255),
    project_document_content MEDIUMBLOB,
    id_proof_name VARCHAR(255),
    id_proof_content MEDIUMBLOB,

    -- Metadata
    job_description TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_application_id (application_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
```

### Critical Observation

❌ **`approved_candidates` table does NOT have an internship_mode or internship_type field!**

- Only has `mode_of_interview` (online/offline for the interview itself)
- This is a data gap for audit trail purposes

---

## 3. FREE INTERNSHIP TABLE SCHEMA

**File Reference**: `database_setup.sql`

```sql
CREATE TABLE IF NOT EXISTS free_internship (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL,
    usn VARCHAR(50) NOT NULL UNIQUE,

    -- Files (as LONGBLOB)
    resume LONGBLOB,
    project LONGBLOB,
    id_card LONGBLOB,

    -- Additional Fields (discovered from code)
    email VARCHAR(100),
    phone VARCHAR(15),
    year VARCHAR(50),
    qualification VARCHAR(50),
    branch VARCHAR(100),
    college VARCHAR(200),
    domain VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_usn (usn)
);

-- Document Store for Large Files
CREATE TABLE free_document_store (
    id INT PRIMARY KEY AUTO_INCREMENT,
    free_internship_application_id INT NOT NULL,
    resume_content MEDIUMBLOB,
    project_document_content MEDIUMBLOB,
    id_proof_content MEDIUMBLOB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (free_internship_application_id) REFERENCES free_internship(id)
);
```

### Note on Mode

- No `internship_mode` field in table
- Mode is **implicit**: "free_internship" table = free mode
- Explicitly stored only when moved to `Selected` table

---

## 4. PAID INTERNSHIP TABLE SCHEMA

**File Reference**: `database_setup.sql`

```sql
CREATE TABLE IF NOT EXISTS paid_internship (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL,
    usn VARCHAR(50) NOT NULL UNIQUE,

    -- Files
    resume LONGBLOB,
    project LONGBLOB,
    id_card LONGBLOB,

    -- Additional Fields
    email VARCHAR(100),
    phone VARCHAR(15),
    year VARCHAR(50),
    qualification VARCHAR(50),
    branch VARCHAR(100),
    college VARCHAR(200),
    domain VARCHAR(100),
    project_description VARCHAR(255),
    project_title VARCHAR(50),
    internship_duration VARCHAR(50),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_usn (usn)
);

-- Document Store for Large Files
CREATE TABLE paid_document_store (
    id INT PRIMARY KEY AUTO_INCREMENT,
    paid_internship_application_id INT NOT NULL,
    resume_content MEDIUMBLOB,
    project_document_content MEDIUMBLOB,
    id_proof_content MEDIUMBLOB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (paid_internship_application_id) REFERENCES paid_internship(id)
);
```

### Note on Mode

- No `internship_mode` field in table
- Mode is **implicit**: "paid_internship" table = paid mode
- Explicitly stored only when moved to `Selected` table

---

## 5. PROPOSED FIX FOR approved_candidates TABLE

### Current Schema Gap

The `approved_candidates` table is a temporary holding area but lacks the internship mode information. This is a data integrity issue.

### Recommended Addition

```sql
-- Add this column to approved_candidates table
ALTER TABLE approved_candidates
ADD COLUMN internship_mode VARCHAR(50) DEFAULT 'free'
AFTER mode_of_interview;

-- Update index
ALTER TABLE approved_candidates
ADD INDEX idx_internship_mode (internship_mode);
```

### Updated Create Statement

```sql
CREATE TABLE approved_candidates (
    usn VARCHAR(50) PRIMARY KEY,
    application_id VARCHAR(20) UNIQUE NOT NULL,
    user_id INT UNIQUE,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL,
    phone_number VARCHAR(15) NOT NULL,

    year VARCHAR(20) NOT NULL,
    qualification VARCHAR(50) NOT NULL,
    branch VARCHAR(100) NOT NULL,
    college VARCHAR(200) NOT NULL,
    domain VARCHAR(100) NOT NULL,

    mode_of_interview VARCHAR(20) DEFAULT 'online',

    -- NEW FIELD TO ADD
    internship_mode VARCHAR(50) DEFAULT 'free',  -- ✅ ADD THIS

    resume_name VARCHAR(255),
    resume_content MEDIUMBLOB,
    project_document_name VARCHAR(255),
    project_document_content MEDIUMBLOB,
    id_proof_name VARCHAR(255),
    id_proof_content MEDIUMBLOB,

    job_description TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_application_id (application_id),
    INDEX idx_internship_mode (internship_mode),  -- ✅ ADD THIS INDEX
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
```

---

## 6. SLOT_BOOKING TABLE (Related to Interview Mode)

The `slot_booking` table stores interview scheduling, related to `mode_of_interview`:

```sql
CREATE TABLE slot_booking (
    id INT PRIMARY KEY AUTO_INCREMENT,
    applicant_id INT NOT NULL,
    slot_date DATE,
    slot_time TIME,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (applicant_id) REFERENCES approved_candidates(user_id)
);
```

---

## 7. MODE VALUE MAPPING

### How Internship Mode is Determined

#### From Table Name (Initial Registration)

| Table Name        | Implicit Mode | Explicit After Moving to Selected |
| ----------------- | ------------- | --------------------------------- |
| `free_internship` | "free"        | `mode_of_internship = 'free'`     |
| `paid_internship` | "paid"        | `mode_of_internship = 'paid'`     |

#### From Request Parameter (At Acceptance)

| URL Parameter | Stored Value                  | Duration |
| ------------- | ----------------------------- | -------- |
| `?type=free`  | `mode_of_internship = 'free'` | 1 month  |
| `?type=paid`  | `mode_of_internship = 'paid'` | 3 months |

#### From HTML Dropdown (Offer Letter Generator)

```html
<select name="internship_type">
  <option value="remote-based opportunity">Remote-based opportunity</option>
  <option value="on-site based opportunity">On-site based opportunity</option>
  <option value="hybrid-based opportunity">Hybrid-based opportunity</option>
</select>
```

**Stored as**: `mode_of_internship` in `Selected` table

---

## 8. COLUMN NAME VARIATIONS

The application is flexible with column names (case-insensitive lookup):

### Email Column Variants (Discovered)

- email, applicant_email, email_address, emailid, mail

### Name Column Variants

- name, full_name, applicant_name, student_name

### USN Column Variants

- usn, roll, rollno, usn_number

### This Flexibility

- Allows the app to work with different table schemas
- Uses function `_resolve_table_name()` in admin_app.py
- Looks for `COLUMN_NAME` from `information_schema.columns`

---

## 9. DATA TYPE SUMMARY FOR INTERNSHIP MODE

| Aspect              | Data Type        | Example                                    | Storage Location                      |
| ------------------- | ---------------- | ------------------------------------------ | ------------------------------------- |
| **Internship Mode** | VARCHAR          | "free", "paid", "remote-based opportunity" | Selected.mode_of_internship           |
| **Interview Mode**  | VARCHAR(20)      | "online", "offline"                        | approved_candidates.mode_of_interview |
| **Candidate ID**    | VARCHAR          | "SIN25FD001"                               | Selected.candidate_id                 |
| **Domain/Role**     | VARCHAR(100)     | "Full Stack Developer"                     | Selected.domain                       |
| **Status**          | ENUM             | "ongoing", "completed"                     | Selected.status                       |
| **Duration**        | INT (calculated) | 1 or 3                                     | Derived from mode_of_internship       |

---

## 10. INDEXING STRATEGY

### Current Indexes in Selected Table

- PRIMARY KEY: `usn`
- UNIQUE: `application_id`
- AUTO_INCREMENT: `id`

### Recommended Indexes for Query Performance

```sql
-- Already optimal for common queries:
-- Find by USN: uses PRIMARY KEY (usn)
-- Find by Application ID: uses UNIQUE index (application_id)

-- Useful additions:
ALTER TABLE Selected ADD INDEX idx_mode_of_internship (mode_of_internship);
ALTER TABLE Selected ADD INDEX idx_status (status);
ALTER TABLE Selected ADD INDEX idx_approved_date (approved_date);
ALTER TABLE Selected ADD INDEX idx_status_mode (status, mode_of_internship);
```

---

## 11. BLOB STORAGE CONSIDERATIONS

| Table               | BLOB Column                                                | Max Size | Current Type             |
| ------------------- | ---------------------------------------------------------- | -------- | ------------------------ |
| free_internship     | resume, project, id_card                                   | 4GB      | LONGBLOB                 |
| free_document_store | resume_content, project_document_content, id_proof_content | 16MB     | MEDIUMBLOB               |
| paid_internship     | resume, project, id_card                                   | 4GB      | LONGBLOB                 |
| paid_document_store | resume_content, project_document_content, id_proof_content | 16MB     | MEDIUMBLOB               |
| approved_candidates | resume_content, project_document_content, id_proof_content | 16MB     | MEDIUMBLOB (LargeBinary) |
| Selected            | internship_project_content, offer_letter_pdf               | 16MB     | MEDIUMBLOB               |

---

## KEY TAKEAWAYS

1. **Primary Mode Storage**: `Selected.mode_of_internship` (VARCHAR)
2. **Possible Values**: "free", "paid", "remote-based opportunity", "hybrid-based opportunity", "on-site based opportunity"
3. **When Set**: During acceptance, when candidate moves to Selected table
4. **Gap**: `approved_candidates` table should also store this for better audit trail
5. **Related Field**: `mode_of_interview` (different from internship_mode - it's about how interview is conducted)
6. **Associated Data**: candidate_id, domain, roles, completion_date are also set at same time
