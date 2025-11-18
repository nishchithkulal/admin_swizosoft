# Quick Reference: Internship Mode Data Location & Usage

## 📊 Quick Lookup Table

### Where Internship Mode is Stored

| Table Name              | Column Name          | Type    | Values                                                                                    | Primary Use                |
| ----------------------- | -------------------- | ------- | ----------------------------------------------------------------------------------------- | -------------------------- |
| **Selected**            | `mode_of_internship` | VARCHAR | free, paid, remote-based opportunity, hybrid-based opportunity, on-site based opportunity | Main tracking (✅ Primary) |
| **approved_candidates** | ❌ NOT STORED        | -       | -                                                                                         | (Gap: Should store this)   |
| **free_internship**     | ❌ Implicit          | -       | Implicitly "free"                                                                         | Registration table         |
| **paid_internship**     | ❌ Implicit          | -       | Implicitly "paid"                                                                         | Registration table         |

---

## 🔍 Field Lookup by Field Name

### `mode_of_interview` (⚠️ NOT the same as internship mode)

- **Table**: `approved_candidates`, `Selected` (sometimes)
- **Type**: VARCHAR(20), default='online'
- **Values**: 'online', 'offline'
- **Purpose**: Interview mode (online vs offline interview)
- **NOT internship mode** - this is different!

### `mode_of_internship` (✅ The internship mode field)

- **Table**: `Selected` only
- **Type**: VARCHAR
- **Values**:
  - "free" (1 month default duration)
  - "paid" (3 months default duration)
  - "remote-based opportunity" (3 months)
  - "hybrid-based opportunity" (3 months)
  - "on-site based opportunity" (3 months)
- **Purpose**: Tracks type/mode of internship assigned
- **When set**: When candidate is accepted and moved to Selected table

---

## 📍 Line Numbers in Key Files

### admin_app.py

| Line Range | Function                             | What It Does                                                            |
| ---------- | ------------------------------------ | ----------------------------------------------------------------------- |
| 1317-1341  | `handle_approved_candidate_accept()` | UPDATE Selected with mode_of_internship for approved candidates         |
| 1358-1367  | `handle_approved_candidate_accept()` | INSERT into Selected with mode_of_internship from internship_type param |
| 1663-1850  | `admin_accept()`                     | Main accept handler - sets mode to "free" or "paid"                     |
| 1772-1777  | `admin_accept()`                     | INSERT for paid: mode_of_internship='paid'                              |
| 3577       | Certificate generation               | SELECT mode_of_internship for offer letter                              |
| 3605       | Certificate generation               | Extract internship_type from mode_of_internship                         |

### models.py (SQLAlchemy)

| Line Range | Model             | Fields Related to Mode                              |
| ---------- | ----------------- | --------------------------------------------------- |
| 24         | ApprovedCandidate | `mode_of_interview` = VARCHAR(20), default='online' |
| -          | ApprovedCandidate | ❌ NO internship_mode/internship_type field         |

---

## 🗄️ SQL Query Examples

### Get Internship Mode for a Candidate

```sql
SELECT mode_of_internship, name, usn, domain, candidate_id
FROM Selected
WHERE usn = 'CS23001';
```

### Get All Candidates by Internship Mode

```sql
SELECT usn, name, domain, mode_of_internship, status
FROM Selected
WHERE mode_of_internship = 'paid'
ORDER BY approved_date DESC;
```

### Get Mode Statistics

```sql
SELECT mode_of_internship, COUNT(*) as count
FROM Selected
WHERE status = 'ongoing'
GROUP BY mode_of_internship;
```

---

## 📡 API Endpoints for Internship Data

### Get Selected Candidates (includes mode_of_internship)

```
GET /admin/api/get-selected
```

**Returns**: All Selected records with `mode_of_internship`

### Get Completed Candidates

```
GET /admin/api/get-completed-candidates
```

**Returns**: Completed internships with `mode_of_internship`

### Get Single Candidate

```
GET /admin/api/get-selected-candidate/<usn_or_id>
```

**Returns**: Full Selected record with `mode_of_internship`

### Accept Application (Sets mode_of_internship)

```
POST /accept/<user_id>?type=free|paid
```

**Sets**: `mode_of_internship` to the type parameter

---

## 🔄 Data Flow: How Internship Mode Gets Set

### Step 1: Registration

```
User submits form → stored in free_internship OR paid_internship table
(mode is implicit from table name, not explicitly stored)
```

### Step 2: Admin Accepts

```
/accept/<user_id>?type=free
                        ↓
admin_accept() function reads type parameter
                        ↓
For PAID internships:
  - Extracts from paid_internship table
  - mode_of_internship = 'paid' (hardcoded)
  - INSERT into Selected with mode_of_internship='paid'

For FREE internships:
  - Extracts from free_internship table
  - Moves to approved_candidates first
  - Then later to Selected with mode_of_internship='free'
```

### Step 3: Candidate Selected

```
Selected table now has:
  - candidate_id: SIN25FD001
  - mode_of_internship: 'free' or 'paid' or other
  - status: 'ongoing'
  - completion_date: calculated from duration
```

---

## ⚠️ Important Notes

1. **`approved_candidates` Gap**: The approved_candidates table does NOT store internship_mode/type. When a candidate moves from free_internship to approved_candidates to Selected, the mode info is lost in the intermediate stage.

2. **`mode_of_interview` ≠ `mode_of_internship`**:

   - `mode_of_interview`: How the interview is conducted (online/offline)
   - `mode_of_internship`: Type of internship (free/paid/remote/etc)
   - They are different fields!

3. **Table Name Variations**:

   - `free_internship` or `free_internship_application` (same thing, naming varies)
   - `paid_internship` or `paid_internship_application` (same thing, naming varies)
   - Application resolves this with `_resolve_table_name()` function

4. **Duration Calculation**:
   ```
   "free" internship → 1 month (DATE_ADD(CURDATE(), INTERVAL 1 MONTH))
   "paid" internship → 3 months (DATE_ADD(CURDATE(), INTERVAL 3 MONTH))
   Other types → 3 months default
   ```

---

## 🛠️ How to Query Internship Mode

### By Python (admin_app.py)

```python
# Get mode from Selected table
cursor.execute("SELECT mode_of_internship FROM Selected WHERE usn = %s", (usn_val,))
result = cursor.fetchone()
mode = result.get('mode_of_internship')  # Returns: 'free', 'paid', etc.
```

### By JavaScript (Frontend)

```javascript
// From API response
const candidate = response.data;
const internshipMode = candidate.mode_of_internship; // 'free', 'paid', etc.
```

### Direct SQL

```sql
SELECT * FROM Selected
WHERE mode_of_internship = 'paid'
AND status = 'ongoing'
LIMIT 10;
```

---

## 📋 Checklist: What Data is Available Where

### Registration Stage (free/paid_internship tables)

- ✅ name, email, phone, usn, year, qualification, branch, college, domain
- ✅ Resume, project document, ID proof files
- ❌ Internship mode (only implicit from table name)

### Approved Stage (approved_candidates table)

- ✅ All registration fields
- ✅ mode_of_interview (interview mode: online/offline)
- ❌ Internship mode/type (NOT stored)

### Selected Stage (Selected table)

- ✅ All registration fields
- ✅ **mode_of_internship** (the actual internship type: free/paid/remote/hybrid/on-site)
- ✅ candidate_id (generated ID: SIN25FD001 format)
- ✅ status, approved_date, completion_date, roles

---

## 🎯 Summary

**Main Finding**: Internship mode/type IS properly tracked in the **`Selected.mode_of_internship`** field, but it's NOT stored in the intermediate `approved_candidates` table, which could be improved for better audit trails.

**Primary Storage Location**: `Selected` table, column `mode_of_internship`

**Values**: "free", "paid", "remote-based opportunity", "hybrid-based opportunity", "on-site based opportunity"

**When Set**: When admin accepts a candidate and moves them to Selected table
