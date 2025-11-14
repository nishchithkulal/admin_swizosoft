# 🚀 QUICK REFERENCE CARD
## Swizosoft Admin Portal

---

## ⚡ 5-MINUTE SETUP

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Create database (in MySQL)
# Copy-paste contents of database_setup.sql

# 3. Run application
python app.py

# 4. Open browser
http://localhost:5000

# 5. Login
Username: admin
Password: admin123
```

---

## 📍 KEY LOCATIONS

| Item | Location |
|------|----------|
| Main App | `app.py` |
| Config | `config.py` |
| Login Page | `templates/login.html` |
| Dashboard | `templates/dashboard.html` |
| Styles | `static/css/` |
| Scripts | `static/js/` |
| Database Setup | `database_setup.sql` |
| Upload Tool | `upload_internship.py` |

---

## 🔑 CREDENTIALS

```
Username: admin
Password: admin123
```

---

## 📞 URLS

| Page | URL |
|------|-----|
| Login | http://localhost:5000/login |
| Dashboard | http://localhost:5000/dashboard |
| Logout | http://localhost:5000/logout |

---

## 🗄️ DATABASE INFO

```
Host: srv1128.hstgr.io
User: u973091162_swizosoft_int
Password: Internship@Swizosoft1
Database: u973091162_internship_swi

Tables:
- free_internship
- paid_internship
```

---

## 📚 DOCUMENTS

| Document | Purpose |
|----------|---------|
| `START_HERE.md` | Entry point |
| `QUICKSTART.md` | 5-min setup |
| `README.md` | Full docs |
| `INSTALLATION.md` | Detailed setup |
| `DEPLOYMENT.md` | Production |

---

## 🛠️ COMMON COMMANDS

```bash
# Install dependencies
pip install -r requirements.txt

# Run app
python app.py

# Upload tool
python upload_internship.py

# Test database
# (Use upload_internship.py → Option 7)
```

---

## ❌ TROUBLESHOOTING

| Issue | Solution |
|-------|----------|
| Python not found | Install Python 3.7+ |
| MySQL not found | Install MySQL Server |
| Can't connect DB | Check credentials in config.py |
| Port 5000 in use | Change port in app.py |
| Files not showing | Verify BLOB in database |

---

## 🎨 CUSTOMIZATION

| Change | Location |
|--------|----------|
| Admin password | `config.py` line 36 |
| Port number | `app.py` last line |
| Colors | `static/css/dashboard.css` |
| Company name | `templates/*.html` |
| Database | `config.py` |

---

## ✅ FILES CREATED (15 Total)

**Backend (4)**
- app.py
- config.py
- requirements.txt
- upload_internship.py

**Frontend (5)**
- templates/login.html
- templates/dashboard.html
- static/css/login.css
- static/css/dashboard.css
- static/js/dashboard.js

**Database (2)**
- database_setup.sql
- .env.example

**Config (2)**
- .gitignore
- run.bat

**Docs (6)**
- START_HERE.md
- QUICKSTART.md
- INSTALLATION.md
- README.md
- PROJECT_SUMMARY.md
- DEPLOYMENT.md
- COMPLETION_REPORT.md

---

## 🎯 FEATURES AT A GLANCE

✅ Admin Login  
✅ Dashboard with 2 Tables  
✅ File Viewing/Download  
✅ MySQL Integration  
✅ Session Management  
✅ Responsive Design  
✅ Professional UI  
✅ Upload Tool  

---

## 📊 API ENDPOINTS

```
GET  /                 - Redirect
POST /login            - Login
GET  /dashboard        - Dashboard
GET  /logout           - Logout
GET  /api/get-internships?type=free|paid
GET  /api/view-file/<id>/<type>?type=free|paid
GET  /api/get-resume/<id>?type=free|paid
GET  /api/get-project/<id>?type=free|paid
GET  /api/get-id/<id>?type=free|paid
```

---

## 💾 DATABASE TABLES

**Both tables have:**
- id (PRIMARY KEY)
- name
- usn (UNIQUE)
- resume (BLOB)
- project (BLOB)
- id_card (BLOB)
- created_at

---

## 🔐 ADMIN CREDENTIALS

```
Username: admin
Password: admin123
```

⚠️ Change these for production!

---

## 📱 RESPONSIVE BREAKPOINTS

- Desktop: 1200px+
- Tablet: 768px - 1199px
- Mobile: < 768px

---

## 🎓 LEARN MORE

- [Flask Docs](https://flask.palletsprojects.com/)
- [MySQL Docs](https://dev.mysql.com/doc/)
- [Python Docs](https://www.python.org/doc/)
- [MDN Web Docs](https://developer.mozilla.org/)

---

## 📞 GETTING HELP

1. Check documentation in `/`
2. Run `python upload_internship.py`
3. Test DB connection (option 7)
4. Check error logs
5. Review browser console (F12)

---

## 🎉 READY TO GO!

```bash
cd c:\Users\HP\OneDrive\Desktop\Swizosoft
pip install -r requirements.txt
python app.py
```

Then open: **http://localhost:5000**

---

**Version**: 1.0  
**Status**: ✅ Ready  
**Created**: Nov 14, 2025
