# Candidate ID System - Quick Reference

## Summary
When an admin accepts a paid internship candidate, a unique ID is automatically generated and stored in the `Selected` table's `candidate_id` column.

**Format:** `SIN` + YY (year) + XX (domain code) + NNN (counter)

- **Examples:**
- `SIN25FD001` - First Full Stack Developer in 2025
- `SIN25AI002` - Second Artificial Intelligence in 2025
- `SIN25DS001` - First Data Science in 2025

---

## Domain Codes (Quick Reference)

```
FD = FULL STACK DEVELOPER
AI = ARTIFICIAL INTELLIGENCE
DS = DATA SCIENCE
DA = DATA ANALYSIS
ML = MACHINE LEARNING
AD = ANDROID APP DEVELOPMENT
SQ = SQL DEVELOPER
HR = HUMAN RESOURCE
```

---

## How It Works

### Step 1: Admin Accepts Candidate
- Navigate to **Approved Candidates** page
- Click **Accept** on a candidate from paid internship

### Step 2: System Generates ID
- Extracts candidate's domain (e.g., "FULL STACK DEVELOPER")
- Gets current year's last 2 digits (2025 → 25)
- Converts domain to code (FULL STACK DEVELOPER → FD)
- Queries Selected table for highest SIN25FD* ID
- If SIN25FD002 exists, generates SIN25FD003
- If none exist, generates SIN25FD001

### Step 3: Store in Database
- ID is stored in `Selected.candidate_id`
- Candidate record moved from paid_internship to Selected
- Original record deleted

---

## File Changes

### Modified Files:
1. **admin_app.py** (2299 lines)
   - Added `DOMAIN_CODES` dictionary (lines ~155-165)
   - Added `get_domain_code()` function (lines ~167-171)
   - Added `generate_candidate_id()` function (lines ~173-221)
   - Updated accept flow INSERT statement (line ~1129-1140)
   - Updated accept flow UPDATE statement (line ~1075-1097)

### New Files:
1. **CANDIDATE_ID_GENERATION.md** - Full documentation
2. **CANDIDATE_ID_QUICKREF.md** - This file

---

## Code Examples

### Generate ID for a Domain
```python
from admin_app import generate_candidate_id

# Generate for FULL STACK DEVELOPER
candidate_id = generate_candidate_id("FULL STACK DEVELOPER")
# Returns: "SIN25FD001" (or next sequential)

# Generate for DATA SCIENCE
candidate_id = generate_candidate_id("DATA SCIENCE")
# Returns: "SIN25DS001" (or next sequential)
```

### Database Query to Get All IDs by Domain
```sql
-- Count by domain in 2025
SELECT 
    SUBSTRING(candidate_id, 6, 2) as domain_code,
    COUNT(*) as count
FROM Selected 
WHERE candidate_id LIKE 'SIN25%'
GROUP BY SUBSTRING(candidate_id, 6, 2)
ORDER BY domain_code;
```

### Get Next ID for a Domain
```sql
-- Get the next ID that would be generated for FULL STACK (FD) in 2025
SELECT candidate_id FROM Selected 
WHERE candidate_id LIKE 'SIN25FD%' 
ORDER BY candidate_id DESC 
LIMIT 1;
```

---

## Testing Checklist

- [ ] Accept a "FULL STACK DEVELOPER" candidate → Should get SIN25FD001
- [ ] Accept another "FULL STACK DEVELOPER" → Should get SIN25FD002
- [ ] Accept an "ARTIFICIAL INTELLIGENCE" → Should get SIN25AI001
- [ ] Accept another "DATA SCIENCE" → Should get SIN25DS002 (if one already exists)
- [ ] Check Selected table - all records have unique candidate_id
- [ ] Update existing candidate - candidate_id should not change
- [ ] Test with year change (Jan 1, 2026) - new IDs should start with SIN26

---

## Troubleshooting

### Issue: candidate_id is NULL
**Cause:** Either the generation failed or it's a legacy record
**Solution:** Manually update the field or re-accept the candidate

### Issue: Duplicate candidate_id
**Cause:** Manual database edits or system error
**Solution:** Contact developer to fix uniqueness constraint

### Issue: Wrong domain code in ID
**Cause:** Domain name spelling doesn't match DOMAIN_CODES dictionary
**Solution:** Check domain field spelling, add entry to DOMAIN_CODES if needed

---

## Performance Notes

- ID generation involves 1 database query (SELECT for highest ID)
- Query uses LIKE with wildcard - ensure `candidate_id` column is indexed
- Generation happens during accept flow (minimal impact)
- No external API calls or complex logic

---

## Future Considerations

1. Add candidate_id to frontend display (Selected Candidates page)
2. Add admin UI to manually edit/regenerate IDs if needed
3. Export/Report IDs by domain and year
4. Add validation to reject malformed IDs
5. Implement ID recycling policy for failed candidates

---

## Support

For issues or questions about candidate ID generation:
1. Check `CANDIDATE_ID_GENERATION.md` for detailed documentation
2. Review `admin_app.py` lines 155-221 for implementation
3. Check application logs for generation errors
4. Query `Selected` table to verify ID storage
