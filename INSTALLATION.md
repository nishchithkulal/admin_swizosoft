# Installation Guide - Swizosoft Admin Portal

## System Requirements

- **Operating System**: Windows 7+, macOS 10.14+, or Linux
- **Python**: 3.7 or higher
- **MySQL Server**: 5.7 or higher
- **Browser**: Chrome 90+, Firefox 88+, Safari 14+, or Edge 90+

## Complete Installation Steps

### 1. Prerequisites Installation

#### Install Python
1. Download Python from https://www.python.org/downloads/
2. During installation, check "Add Python to PATH"
3. Verify installation:
   ```bash
   python --version
   ```

#### Install MySQL
1. Download MySQL from https://dev.mysql.com/downloads/mysql/
2. Run the installer and follow the setup wizard
3. Note your root password
4. Verify installation:
   ```bash
   mysql --version
   ```

### 2. Project Setup

#### Clone or Download Project
Download the Swizosoft project and extract it to your desired location.

#### Open Terminal/Command Prompt
Navigate to the project directory:
```bash
cd c:\Users\HP\OneDrive\Desktop\Swizosoft
```

#### Create Virtual Environment
```bash
python -m venv venv
```

#### Activate Virtual Environment
- **Windows (PowerShell)**:
  ```bash
  .\venv\Scripts\Activate.ps1
  ```
- **Windows (Command Prompt)**:
  ```bash
  .\venv\Scripts\activate.bat
  ```
- **macOS/Linux**:
  ```bash
  source venv/bin/activate
  ```

#### Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 3. Database Configuration

#### Connect to MySQL
```bash
mysql -h srv1128.hstgr.io -u u973091162_swizosoft_int -p
```
Password: `Internship@Swizosoft1`

#### Create Database Tables
Run the SQL commands from `database_setup.sql`:

1. Open `database_setup.sql` file
2. Copy and paste the SQL commands in MySQL client
3. Or run directly:
   ```bash
   mysql -h srv1128.hstgr.io -u u973091162_swizosoft_int -p u973091162_internship_swi < database_setup.sql
   ```

#### Verify Tables
```sql
USE u973091162_internship_swi;
SHOW TABLES;
DESCRIBE free_internship;
DESCRIBE paid_internship;
```

### 4. Test Database Connection

Run the test script:
```bash
python upload_internship.py
```

Select option 7 to test the database connection.

### 5. Add Sample Data (Optional)

You can add sample data to test the application:

```sql
INSERT INTO free_internship (name, usn) VALUES ('John Doe', 'USN001');
INSERT INTO free_internship (name, usn) VALUES ('Jane Smith', 'USN002');
INSERT INTO paid_internship (name, usn) VALUES ('Bob Johnson', 'USN003');
INSERT INTO paid_internship (name, usn) VALUES ('Alice Brown', 'USN004');
```

### 6. Run the Application

#### Option A: Using Python Directly
```bash
python app.py
```

#### Option B: Using Batch Script (Windows)
```bash
run.bat
```

#### Option C: Using Upload Tool
```bash
python upload_internship.py
```
Select option 1 or 2 to upload records.

### 7. Access the Application

1. Open your browser
2. Go to `http://localhost:5000`
3. You will be redirected to the login page
4. Login with:
   - **Username**: `admin`
   - **Password**: `admin123`

## File Upload Guide

### Using the Upload Tool

1. Run the tool:
   ```bash
   python upload_internship.py
   ```

2. Choose option 1 or 2 to upload a single record
3. Enter the required information:
   - Name
   - USN
   - Paths to files (resume, project, ID card)

### Batch Upload

Directory structure:
```
uploads/
├── John_Doe_USN001/
│   ├── resume.pdf
│   ├── project.pdf
│   └── id.jpg
├── Jane_Smith_USN002/
│   ├── resume.pdf
│   ├── project.pdf
│   └── id.jpg
```

Then run:
```bash
python upload_internship.py
```
Select option 6 and provide the directory path.

## Configuration

### Change Admin Password

Edit `config.py`:
```python
class Config:
    ADMIN_PASSWORD = 'your-new-password'
```

### Change Database Credentials

Edit `config.py` or set environment variables:
```bash
$env:DB_HOST = 'your-host'
$env:DB_USER = 'your-user'
$env:DB_PASSWORD = 'your-password'
$env:DB_NAME = 'your-database'
```

### Change Application Port

Edit `app.py`, last line:
```python
app.run(debug=True, host='0.0.0.0', port=8000)  # Change 5000 to 8000
```

## Troubleshooting

### Python Not Found
- Install Python from https://www.python.org/
- Add Python to PATH during installation
- Restart terminal/command prompt

### MySQLdb Installation Error
Try alternative:
```bash
pip install PyMySQL
```

### Can't Connect to Database
1. Check MySQL server is running
2. Verify credentials in `config.py`
3. Test connection:
   ```bash
   mysql -h srv1128.hstgr.io -u u973091162_swizosoft_int -p
   ```

### Port 5000 Already in Use
Either:
1. Kill the process using the port
2. Change the port in `app.py`

### Files Not Uploading
1. Verify file format (PDF for docs, JPG/PNG for images)
2. Check file size (MySQL `max_allowed_packet` limit)
3. Use the upload tool to verify file paths

## Uninstallation

1. Deactivate virtual environment:
   ```bash
   deactivate
   ```

2. Remove the project folder:
   ```bash
   rmdir /s c:\Users\HP\OneDrive\Desktop\Swizosoft
   ```

## Getting Help

1. Check README.md for full documentation
2. Check QUICKSTART.md for quick start guide
3. Review error messages carefully
4. Check browser console for JavaScript errors (F12)
5. Check Flask debug output for Python errors

## Next Steps

1. ✅ Installation complete
2. 📝 Read QUICKSTART.md for quick start
3. 📋 Read README.md for full documentation
4. 🚀 Start uploading internship records
5. 🔒 Change admin credentials for production
6. 🌐 Deploy to production server (optional)

---

**Ready to go!** Your Swizosoft Admin Portal is now installed and ready to use.
