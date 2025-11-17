# Job Description Management Guide

## Overview
The Job Description management interface allows administrators to add, edit, and delete job descriptions for different internship domains.

## Features Implemented

### 1. **View Job Descriptions**
- Navigate to **Job Description** tab in the admin dashboard
- All existing job descriptions are displayed as domain buttons
- Click on any domain button to preview its full job description

### 2. **Add New Job Description**
- Click the **"+ Add New"** button in the top-right corner
- Modal dialog opens with fields for:
  - **Domain Name**: The name of the internship domain (e.g., "Full Stack Developer")
  - **Job Description**: The full job description text
- Click **"Add"** button to save the new entry
- New domain button appears in the domains list automatically
- Data is saved to the `job_description` table in the database

### 3. **Edit Existing Job Description**
- Click on any domain button to select it
- Click the **"Edit"** button that appears below the preview
- Modal opens with current domain name and job description pre-filled
- Make your changes to either field
- Click **"Save"** to update the database
- Changes are immediately reflected in the UI and database

### 4. **Delete Job Description**
- Click on any domain button to select it
- Click the **"Delete"** button (red, appears below preview)
- Confirm the deletion when prompted
- Domain is removed from the UI and database
- The job description is also cleared from any associated `approved_candidates` records

## Database Schema

The system uses a `job_description` table:

```sql
CREATE TABLE IF NOT EXISTS job_description (
    id INT AUTO_INCREMENT PRIMARY KEY,
    domain VARCHAR(255),
    description TEXT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
```

## Backend Workflow

### Add Operation
- **Route**: POST to `/admin/job-description`
- **Parameters**: `action=add`, `domain`, `description`
- **Database**: Inserts new row with domain name and job description
- **Propagation**: Updates `approved_candidates` table with new job description for matching domain

### Save/Edit Operation
- **Route**: POST to `/admin/job-description`
- **Parameters**: `action=save`, `id`, `domain`, `description`
- **Database**: Updates row by ID with new domain name and description
- **Propagation**: Updates `approved_candidates` records for the domain

### Delete Operation
- **Route**: POST to `/admin/job-description`
- **Parameters**: `action=delete`, `id` (or `domain`)
- **Database**: Removes entry from `job_description` table
- **Propagation**: Clears `job_description` field in `approved_candidates` for the domain

## Frontend Features

### Modal Dialog
- Clean, responsive design with gradient header
- Form validation (domain and description required)
- Close button (×) or click outside to close
- Escape key also closes the modal
- Focus automatically set to domain name field on open

### User Feedback
- Edit/Delete buttons only appear when a domain is selected
- Confirmation dialogs for delete operations
- Active domain button highlighted with different color
- Preview shows full formatted text with proper line breaks

## Testing Checklist

- [ ] Click "Add New" and add a test domain with description
- [ ] Verify new domain appears in the list
- [ ] Click on the new domain to view it
- [ ] Click "Edit" and modify the description
- [ ] Click "Save" and verify changes appear
- [ ] Refresh page and verify changes persisted in DB
- [ ] Click on another domain and click "Delete"
- [ ] Confirm deletion and verify it's removed from UI and DB
- [ ] Verify edits/additions also update approved_candidates table

## Technical Notes

- Form submission is via POST to maintain REST conventions
- All input is properly escaped to prevent XSS attacks
- Database operations include error handling and fallback strategies
- Table schema is created automatically on first access if it doesn't exist
- Compatible with different MySQL table schema variations
