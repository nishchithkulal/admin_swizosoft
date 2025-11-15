# Approved Candidates Database Setup

## Overview
The `approved_candidates` table is used to store detailed information about approved internship candidates including their resumes, ID proofs, and project documents.

## Table Schema

| Field | Type | Details |
|-------|------|---------|
| `usn` | VARCHAR(50) | **PRIMARY KEY** - Unique Student Number |
| `application_id` | INT | Unique application identifier |
| `name` | VARCHAR(255) | Candidate's full name |
| `email` | VARCHAR(255) | Candidate's email address |
| `phone_number` | VARCHAR(20) | Candidate's phone number |
| `year` | VARCHAR(50) | Academic year (e.g., "3rd Year") |
| `qualification` | VARCHAR(255) | Educational qualification (e.g., "BTech") |
| `branch` | VARCHAR(255) | Department/Branch (e.g., "Computer Science") |
| `college` | VARCHAR(255) | College/Institute name |
| `domain` | VARCHAR(255) | Internship domain (e.g., "AI", "Web Development") |
| `mode_of_interview` | ENUM('online', 'offline') | Interview mode preference |
| `resume_name` | VARCHAR(255) | Original resume filename |
| `resume_content` | LONGBLOB | Resume file binary data (MEDIUMBLOB equivalent) |
| `project_document_name` | VARCHAR(255) | Project document filename |
| `project_document_content` | LONGBLOB | Project document binary data (MEDIUMBLOB equivalent) |
| `id_proof_name` | VARCHAR(255) | ID proof filename |
| `id_proof_content` | LONGBLOB | ID proof binary data (MEDIUMBLOB equivalent) |
| `created_at` | DATETIME | Record creation timestamp |
| `updated_at` | DATETIME | Last update timestamp |

## Setup Instructions

### 1. Create the Table
Run the initialization script to create the `approved_candidates` table:

```bash
python init_db.py
```

Expected output:
```
✓ Database initialized successfully!
✓ Table 'approved_candidates' created in database 'u973091162_internship_swi'
```

### 2. Verify Table Creation
From phpMyAdmin or MySQL client:
```sql
DESCRIBE approved_candidates;
```

Or view via phpMyAdmin:
1. Go to your database
2. You should see `approved_candidates` table in the left sidebar
3. Click on it to view structure and data

## Usage in Code

### Insert an approved candidate:
```python
from models import db, ApprovedCandidate

new_candidate = ApprovedCandidate(
    usn='CS21001',
    application_id=42,
    name='John Doe',
    email='john@example.com',
    phone_number='+91-9876543210',
    year='3rd Year',
    qualification='BTech',
    branch='Computer Science',
    college='CANARA ENGINEERING COLLEGE',
    domain='Artificial Intelligence',
    mode_of_interview='online',
    resume_name='john_resume.pdf',
    resume_content=b'<binary data>',  # from reading file
    id_proof_name='john_id.jpg',
    id_proof_content=b'<binary data>',
)
db.session.add(new_candidate)
db.session.commit()
```

### Query approved candidates:
```python
from models import ApprovedCandidate

# Get all approved candidates
all_candidates = ApprovedCandidate.query.all()

# Get specific candidate by USN
candidate = ApprovedCandidate.query.filter_by(usn='CS21001').first()

# Convert to dictionary (JSON-friendly)
candidate_dict = candidate.to_dict()
```

### Update a candidate:
```python
from models import ApprovedCandidate

candidate = ApprovedCandidate.query.filter_by(usn='CS21001').first()
candidate.mode_of_interview = 'offline'
db.session.commit()
```

### Delete a candidate:
```python
from models import ApprovedCandidate

candidate = ApprovedCandidate.query.filter_by(usn='CS21001').first()
db.session.delete(candidate)
db.session.commit()
```

## Integration with Flask

To use this model in your Flask app (`admin_app.py`), add:

```python
from models import db, ApprovedCandidate

# Initialize db with your app
db.init_app(app)

# Make database available in Flask shell
@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'ApprovedCandidate': ApprovedCandidate}
```

## Notes

- **MEDIUMBLOB equivalent**: SQLAlchemy's `LargeBinary` type maps to `LONGBLOB` in MySQL by default, which is sufficient for files up to 4GB
- **Primary Key**: USN is the primary key to ensure uniqueness
- **Unique constraint**: application_id has a unique constraint to prevent duplicates
- **Timestamps**: `created_at` and `updated_at` are automatically managed
- **ENUM**: `mode_of_interview` only accepts 'online' or 'offline'
