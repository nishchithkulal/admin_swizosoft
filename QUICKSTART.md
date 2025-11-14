# Swizosoft Admin Portal - Quick Start Guide

## 🚀 Quick Setup (5 Minutes)

### Step 1: Install Python Dependencies

Open PowerShell in the project directory and run:

```powershell
pip install -r requirements.txt
```

If you encounter issues with MySQLdb, try:

```powershell
pip install mysqlclient
```

### Step 2: Verify Database Connection

Open a command prompt and test the connection:

```powershell
python -c "import MySQLdb; print('MySQLdb installed successfully')"
```

### Step 3: Create Database Tables

Open your MySQL client and run the SQL commands from `database_setup.sql`:

```sql
CREATE TABLE IF NOT EXISTS free_internship (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL,
    usn VARCHAR(50) NOT NULL UNIQUE,
    resume LONGBLOB,
    project LONGBLOB,
    id_card LONGBLOB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_usn (usn)
);

CREATE TABLE IF NOT EXISTS paid_internship (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL,
    usn VARCHAR(50) NOT NULL UNIQUE,
    resume LONGBLOB,
    project LONGBLOB,
    id_card LONGBLOB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_usn (usn)
);
```

### Step 4: Run the Application

```powershell
python app.py
```

You should see output like:
```
 * Running on http://127.0.0.1:5000
 * Debug mode: on
```

### Step 5: Access the Application

Open your browser and navigate to:
```
http://localhost:5000
```

You will be redirected to the login page.

## 🔐 Login Credentials

- **Username**: `admin`
- **Password**: `admin123`

## 📋 What You Can Do

After logging in, you can:

1. **View Free Internship Records** - See all free internship applicants with their details
2. **View Paid Internship Records** - See all paid internship applicants with their details
3. **Download/View Files** - Click on "View Resume", "View Project", or "View ID" to:
   - View PDFs and images in a modal window
   - Download files to your computer

## 🗄️ Adding Data to Database

To add internship records, use SQL INSERT statements:

```sql
-- Add a free internship record
INSERT INTO free_internship (name, usn, resume, project, id_card) 
VALUES ('John Doe', 'USN001', [RESUME_BLOB], [PROJECT_BLOB], [ID_BLOB]);

-- Add a paid internship record
INSERT INTO paid_internship (name, usn, resume, project, id_card) 
VALUES ('Jane Smith', 'USN002', [RESUME_BLOB], [PROJECT_BLOB], [ID_BLOB]);
```

### Uploading Files to Database

You can upload files using Python:

```python
# Example script to upload files
import MySQLdb

conn = MySQLdb.connect(
    host='srv1128.hstgr.io',
    user='u973091162_swizosoft_int',
    passwd='Internship@Swizosoft1',
    db='u973091162_internship_swi'
)

cursor = conn.cursor()

# Read file and insert
with open('resume.pdf', 'rb') as f:
    resume_data = f.read()
    cursor.execute(
        "INSERT INTO free_internship (name, usn, resume) VALUES (%s, %s, %s)",
        ('John Doe', 'USN001', resume_data)
    )
    
conn.commit()
cursor.close()
conn.close()
```

## 🛠️ Troubleshooting

### Issue: "No module named MySQLdb"

**Solution**: Install PyMySQL instead:
```powershell
pip install PyMySQL
```

Then modify the import in `app.py`:
```python
import pymysql
pymysql.install_as_MySQLdb()
```

### Issue: "Can't connect to MySQL server"

**Solution**: 
1. Verify MySQL server is running
2. Check database credentials in `config.py`
3. Test connection with MySQL client:
   ```
   mysql -h srv1128.hstgr.io -u u973091162_swizosoft_int -p
   ```
   Password: `Internship@Swizosoft1`

### Issue: "Tables don't exist"

**Solution**: Run the SQL commands from `database_setup.sql` to create tables

### Issue: Files not displaying

**Solution**:
1. Verify files are stored as BLOB in database
2. Check that files are uploaded correctly
3. Verify file size doesn't exceed MySQL `max_allowed_packet` limit

## 📱 Features Overview

### Dashboard Features

✅ **Two Separate Tables**
- Free Internship table
- Paid Internship table

✅ **Columns**
- Name: Applicant's name
- USN: Unique student number
- View Resume: Download/view resume PDF
- View Project: Download/view project PDF
- View ID: Download/view ID card image (JPG/PNG)

✅ **File Viewing**
- PDFs open in modal viewer
- Images display in browser
- Files can be downloaded

✅ **Session Management**
- Auto-logout after 24 hours
- Logout button in navbar
- Secure session cookies

## 🔒 Security Tips

1. **Change Admin Password** - Update `ADMIN_PASSWORD` in `config.py` for production
2. **Use Environment Variables** - Set database credentials as env vars:
   ```powershell
   $env:DB_HOST = 'srv1128.hstgr.io'
   $env:DB_USER = 'u973091162_swizosoft_int'
   $env:DB_PASSWORD = 'Internship@Swizosoft1'
   $env:DB_NAME = 'u973091162_internship_swi'
   ```
3. **Enable HTTPS** - Use SSL/TLS in production
4. **Strong Secret Key** - Generate with: `python -c "import secrets; print(secrets.token_hex(32))"`
5. **Database Backups** - Regular backups of the database

## 📧 File Formats Supported

- **Resume**: PDF (.pdf)
- **Project**: PDF (.pdf)
- **ID Card**: Image (JPG, PNG)

## 🎨 Customization

### Change Logo/Company Name

Edit `dashboard.html` and `login.html`:
```html
<h1>YOUR_COMPANY_NAME</h1>
```

### Change Colors

Edit `dashboard.css` and `login.css`:
```css
/* Change primary color */
background: linear-gradient(135deg, #YOUR_COLOR 0%, #ANOTHER_COLOR 100%);
```

### Change Session Timeout

Edit `config.py`:
```python
PERMANENT_SESSION_LIFETIME = timedelta(hours=24)  # Change hours as needed
```

## 📞 Support

For issues, check:
1. Database connection settings
2. Table structure matches SQL script
3. File permissions
4. MySQL server status

## 📄 File Structure

```
Swizosoft/
├── app.py                      # Main Flask application
├── config.py                   # Configuration file
├── requirements.txt            # Python dependencies
├── README.md                   # Full documentation
├── QUICKSTART.md              # This file
├── database_setup.sql         # Database initialization script
├── templates/
│   ├── login.html             # Login page
│   └── dashboard.html         # Dashboard page
└── static/
    ├── css/
    │   ├── login.css          # Login styles
    │   └── dashboard.css      # Dashboard styles
    └── js/
        └── dashboard.js       # Dashboard functionality
```

---

**Ready to go!** 🎉 Start the application and begin managing internships.
