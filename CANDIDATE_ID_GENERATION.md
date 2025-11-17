# Candidate ID Generation System

## Overview
The system automatically generates unique candidate IDs for selected internship candidates based on their domain/role and the year of selection.

## Format
```
SIN + YY + XX + NNN
```

- **SIN**: Permanent prefix (constant across all IDs)
- **YY**: Current year (last 2 digits, e.g., 25 for 2025)
- **XX**: Domain code (2 letters, specific to the internship role)
- **NNN**: Sequential counter (001, 002, 003, etc. per domain per year)

## Examples
- `SIN25FD001` - First Full Stack Developer selected in 2025
- `SIN25AI002` - Second Artificial Intelligence selected in 2025
- `SIN25DS001` - First Data Science selected in 2025
- `SIN26HR001` - First Human Resource selected in 2026

## Domain Codes

| Role | Code | Example |
|------|------|---------|
| FULL STACK DEVELOPER | FD | SIN25FD001 |
| ARTIFICIAL INTELLIGENCE | AI | SIN25AI001 |
| DATA SCIENCE | DS | SIN25DS001 |
| DATA ANALYSIS | DA | SIN25DA001 |
| MACHINE LEARNING | ML | SIN25ML001 |
| ANDROID APP DEVELOPMENT | AD | SIN25AD001 |
| SQL DEVELOPER | SQ | SIN25SQ001 |
| HUMAN RESOURCE | HR | SIN25HR001 |

## Implementation Details

### Database Changes
- The `Selected` table already has a `candidate_id` column to store the generated ID
- IDs are generated when a candidate is accepted from the Approved Candidates page (paid internships)

### Code Location
- **Generation Function**: `admin_app.py` - `generate_candidate_id(domain_str, conn)`
- **Domain Mapping**: `admin_app.py` - `DOMAIN_CODES` dictionary
- **Accept Flow**: Modified in `/accept/<int:user_id>` route

### Function: `generate_candidate_id(domain_str, conn=None)`

```python
def generate_candidate_id(domain_str, conn=None):
    """
    Generate unique candidate ID based on domain and year.
    
    Args:
        domain_str: Name of the domain/role (e.g., 'FULL STACK DEVELOPER')
        conn: Database connection (optional; will create if not provided)
    
    Returns:
        Unique candidate ID string (e.g., 'SIN25FS001') or None if error
    
    Process:
        1. Extract year from current date (last 2 digits)
        2. Convert domain name to 2-letter code
        3. Query Selected table for highest counter with that prefix
        4. Increment counter and format with leading zeros
        5. Return formatted candidate_id
    """
```

## Workflow

### When Admin Accepts a Paid Internship Candidate:
1. Admin clicks "Accept" on the Approved Candidates page
2. System fetches candidate details from paid internship table
3. System calls `generate_candidate_id()` with the candidate's domain
4. Unique ID is generated and stored in `Selected.candidate_id`
5. Candidate record is moved to the Selected table
6. Original paid internship record is deleted

### Example Flow:
```
Accept User (Domain: "FULL STACK DEVELOPER")
    ↓
Query Selected table for "SIN25FD%" entries
    ↓
Find highest: "SIN25FD002"
    ↓
Generate next: "SIN25FD003"
    ↓
Insert into Selected table with candidate_id = "SIN25FD003"
```

## Usage in Backend

### During Accept Flow:
```python
# In /accept/<int:user_id> route
candidate_id = generate_candidate_id(domain_val, conn)

# Insert into Selected
INSERT INTO Selected (
    ...fields...,
    candidate_id
) VALUES (
    ...values...,
    candidate_id
)
```

### Update Existing Record:
```python
# If candidate already exists
candidate_id = generate_candidate_id(domain_val, conn)

UPDATE Selected SET
    ...other fields...,
    candidate_id = %s
WHERE usn = %s
```

## Database Query Examples

### Get all candidates for a specific domain:
```sql
SELECT * FROM Selected 
WHERE candidate_id LIKE 'SIN25FD%' 
ORDER BY candidate_id;
```

### Get highest ID for a domain in current year:
```sql
SELECT candidate_id FROM Selected 
WHERE candidate_id LIKE 'SIN25FD%' 
ORDER BY candidate_id DESC 
LIMIT 1;
```

### Get count by domain:
```sql
SELECT 
    SUBSTRING(candidate_id, 6, 2) as domain_code,
    COUNT(*) as count
FROM Selected 
WHERE candidate_id LIKE 'SIN25%'
GROUP BY SUBSTRING(candidate_id, 6, 2);
```

## Error Handling

If candidate ID generation fails:
- The function returns `None`
- An error is logged to the application logger
- The accept process continues (candidate still moved to Selected without candidate_id)
- Admin can manually update the `candidate_id` field if needed

## Future Enhancements

1. **Batch Generation**: Generate IDs for multiple candidates at once
2. **Manual Assignment**: Allow admins to manually edit/reassign candidate IDs
3. **Reporting**: Generate reports showing ID distribution by domain/year
4. **Validation**: Validate ID format and uniqueness on update/insert
5. **Frontend Display**: Show generated candidate_id in the Selected Candidates page

## Testing

### Manual Test Steps:
1. Login to admin panel
2. Go to Approved Candidates page
3. Click "Accept" on a candidate with domain "FULL STACK DEVELOPER"
4. Check Selected table for `candidate_id` = `SIN25FD001` (or next sequential number)
5. Accept another "FULL STACK DEVELOPER" - should get `SIN25FD002`
6. Accept an "ARTIFICIAL INTELLIGENCE" - should get `SIN25AI001`
7. Accept another "ARTIFICIAL INTELLIGENCE" - should get `SIN25AI002`

## Database Integrity

- Each `candidate_id` is unique within the Selected table
- Primary key remains `usn` for backward compatibility
- `candidate_id` should be indexed for fast lookups
- `candidate_id` can be NULL for legacy records before this feature was implemented

## Notes

- Domain names are case-insensitive (matches "FULL STACK DEVELOPER", "Full Stack Developer", etc.)
- Invalid domain names get code "XX" (fallback)
- Counter resets each year (e.g., SIN26FD001 starts fresh in 2026)
- Historical IDs remain unchanged if year changes
