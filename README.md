# Swizosoft Admin Portal

A professional admin portal for managing free and paid internship applications at Swizosoft.

## Features

✅ **Admin Authentication** - Secure login with hardcoded credentials  
✅ **Two Internship Tables** - Separate tables for Free and Paid internships  
✅ **File Management** - View/Download resumes, projects, and ID cards  
✅ **Database Integration** - MySQL database for storing internship data  
✅ **Session Management** - Secure session handling with auto-logout  
✅ **Responsive Design** - Works on desktop and mobile devices  

## Prerequisites

- Python 3.7+
- MySQL Server
- MySQLdb library (requires MySQL development libraries)

## Installation

### 1. Clone or Download the Project

```bash
cd c:\Users\HP\OneDrive\Desktop\Swizosoft
```

### 2. Create a Virtual Environment (Recommended)

```bash
python -m venv venv
.\venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Database Setup

Before running the application, ensure your database tables exist:

```sql
-- Create free_internship table
CREATE TABLE free_internship (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL,
    usn VARCHAR(50) NOT NULL UNIQUE,
    resume LONGBLOB,
    project LONGBLOB,
    id_card LONGBLOB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create paid_internship table
CREATE TABLE paid_internship (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL,
    usn VARCHAR(50) NOT NULL UNIQUE,
    resume LONGBLOB,
    project LONGBLOB,
    id_card LONGBLOB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 5. Run the Application

```bash
python app.py
```

The application will start on `http://localhost:5000`

## Usage

### Login Page
- **URL**: `http://localhost:5000/login`
- **Username**: `admin`
- **Password**: `admin123`

### Dashboard
- After successful login, you'll see two tables:
  - **Free Internship**: All free internship applications
  - **Paid Internship**: All paid internship applications

### Viewing Files

1. Click on "View Resume", "View Project", or "View ID" buttons
2. Files will open in a modal viewer
3. You can also download files by clicking the download option

## File Structure

```
Swizosoft/
├── app.py                          # Flask application
├── requirements.txt                # Python dependencies
├── README.md                       # This file
├── templates/
│   ├── login.html                 # Login page
│   └── dashboard.html             # Dashboard page
└── static/
    ├── css/
    │   ├── login.css              # Login page styles
    │   └── dashboard.css          # Dashboard styles
    └── js/
        └── dashboard.js           # Dashboard functionality
```

## Configuration

The database credentials are configured in `app.py`:

```python
app.config['MYSQL_HOST'] = 'srv1128.hstgr.io'
app.config['MYSQL_USER'] = 'u973091162_swizosoft_int'
app.config['MYSQL_PASSWORD'] = 'Internship@Swizosoft1'
app.config['MYSQL_DB'] = 'u973091162_internship_swi'
```

**Note**: For production, use environment variables instead of hardcoded credentials.

## Security Notes

1. Change the `SECRET_KEY` in `app.py` for production
2. Use strong passwords in production
3. Implement HTTPS
4. Add CSRF protection
5. Sanitize all user inputs
6. Use environment variables for sensitive data

## API Endpoints

### Authentication
- `POST /login` - Admin login
- `GET /logout` - Admin logout

### Dashboard
- `GET /dashboard` - Dashboard page (requires login)
- `GET /api/get-internships?type=free|paid` - Get internship list
- `GET /api/get-resume/<id>?type=free|paid` - Download resume
- `GET /api/get-project/<id>?type=free|paid` - Download project
- `GET /api/get-id/<id>?type=free|paid` - Download ID card
- `GET /api/view-file/<id>/<file_type>?type=free|paid` - View file in modal

## Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Troubleshooting

### MySQLdb Installation Issues

On Windows, you might face issues installing MySQLdb. Try:

```bash
pip install mysqlclient
```

Or use PyMySQL as an alternative:

```bash
pip install Flask-PyMySQL
```

### Database Connection Errors

1. Verify database credentials in `app.py`
2. Check if MySQL server is running
3. Ensure the database and tables exist

### Files Not Displaying

1. Verify files are stored as BLOB in the database
2. Check file size limits in MySQL (max_allowed_packet)
3. Verify file permissions

## Support

For issues or questions, contact the development team.

## License

© 2025 Swizosoft. All rights reserved.
