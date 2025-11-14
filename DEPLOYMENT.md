# Deployment Guide - Swizosoft Admin Portal

## Local Development Setup

### Quick Start
```bash
# Navigate to project
cd c:\Users\HP\OneDrive\Desktop\Swizosoft

# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run application
python app.py
```

Visit: http://localhost:5000

---

## Production Deployment

### Option 1: Using Gunicorn (Linux/macOS)

#### 1. Install Gunicorn
```bash
pip install gunicorn
```

#### 2. Update requirements.txt
```bash
pip freeze > requirements.txt
```

#### 3. Create wsgi.py
```python
from app import app

if __name__ == "__main__":
    app.run()
```

#### 4. Run with Gunicorn
```bash
gunicorn -w 4 -b 0.0.0.0:5000 wsgi:app
```

### Option 2: Using Waitress (Windows)

#### 1. Install Waitress
```bash
pip install waitress
```

#### 2. Create serve.py
```python
from waitress import serve
from app import app

if __name__ == '__main__':
    serve(app, host='0.0.0.0', port=5000)
```

#### 3. Run with Waitress
```bash
python serve.py
```

### Option 3: Using IIS (Windows Server)

#### 1. Install Python on Server
Download and install Python 3.9+ on Windows Server.

#### 2. Install FastCGI Support
Install Python Fast CGI module via Web Platform Installer.

#### 3. Configure IIS
- Create new website
- Point to project directory
- Configure FastCGI handler
- Set proper permissions

#### 4. Configure web.config
```xml
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <system.webServer>
        <handlers>
            <add name="Python FastCGI" 
                 path="*" 
                 verb="*" 
                 modules="FastCgiModule" 
                 scriptProcessor="C:\Python39\python.exe|C:\Python39\lib\site-packages\wfastcgi.py" 
                 resourceType="Unspecified" 
                 requireAccess="Script" />
        </handlers>
    </system.webServer>
</configuration>
```

---

## Docker Deployment

### 1. Create Dockerfile
```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV FLASK_APP=app.py
ENV FLASK_ENV=production

EXPOSE 5000

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
```

### 2. Create docker-compose.yml
```yaml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "5000:5000"
    environment:
      - FLASK_ENV=production
      - DB_HOST=srv1128.hstgr.io
      - DB_USER=u973091162_swizosoft_int
      - DB_PASSWORD=Internship@Swizosoft1
      - DB_NAME=u973091162_internship_swi
```

### 3. Build and Run
```bash
docker-compose up --build
```

---

## Environment Variables for Production

Create `.env` file:
```
FLASK_ENV=production
SECRET_KEY=your-very-long-random-secret-key
DB_HOST=srv1128.hstgr.io
DB_USER=u973091162_swizosoft_int
DB_PASSWORD=Internship@Swizosoft1
DB_NAME=u973091162_internship_swi
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your-strong-password
SESSION_COOKIE_SECURE=True
```

---

## HTTPS/SSL Configuration

### 1. Get SSL Certificate
- Use Let's Encrypt (free)
- Or purchase from certificate authority

### 2. Configure in app.py
```python
if __name__ == '__main__':
    app.run(
        debug=False,
        ssl_context=('cert.pem', 'key.pem'),
        host='0.0.0.0',
        port=443
    )
```

### 3. Or use nginx/Apache as reverse proxy
Configure reverse proxy to handle SSL and forward to Flask.

---

## Nginx Configuration Example

```nginx
server {
    listen 443 ssl;
    server_name yourdomain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## Database Backup & Recovery

### Create Backup
```bash
mysqldump -h srv1128.hstgr.io -u u973091162_swizosoft_int -p u973091162_internship_swi > backup.sql
```

### Restore Backup
```bash
mysql -h srv1128.hstgr.io -u u973091162_swizosoft_int -p u973091162_internship_swi < backup.sql
```

### Automated Backup (Linux)
```bash
# backup.sh
#!/bin/bash
BACKUP_DIR="/backups/swizosoft"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

mysqldump -h srv1128.hstgr.io -u u973091162_swizosoft_int -p"$DB_PASSWORD" \
  u973091162_internship_swi > "$BACKUP_DIR/backup_$DATE.sql"
```

Crontab entry:
```
0 2 * * * /path/to/backup.sh
```

---

## Performance Optimization

### 1. Add Database Indexes
```sql
CREATE INDEX idx_name ON free_internship(name);
CREATE INDEX idx_usn ON free_internship(usn);
CREATE INDEX idx_created_at ON free_internship(created_at);
```

### 2. Enable Caching
```python
from flask_caching import Cache

cache = Cache(app, config={'CACHE_TYPE': 'simple'})

@app.route('/api/get-internships')
@cache.cached(timeout=300)
def get_internships():
    # ...
```

### 3. Compress Responses
```python
from flask_compress import Compress
Compress(app)
```

### 4. Use Connection Pooling
```python
from flask_mysqldb import MySQL

app.config['MYSQL_POOL_SIZE'] = 5
app.config['MYSQL_POOL_TIMEOUT'] = 10
```

---

## Security Hardening

### 1. Update config.py
```python
class ProductionConfig:
    DEBUG = False
    TESTING = False
    SECRET_KEY = os.environ.get('SECRET_KEY')
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Strict'
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB file limit
```

### 2. Add CSRF Protection
```python
from flask_wtf.csrf import CSRFProtect

csrf = CSRFProtect(app)
```

### 3. Add Rate Limiting
```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(app, key_func=get_remote_address)

@app.route('/login', methods=['POST'])
@limiter.limit("5 per minute")
def login():
    # ...
```

### 4. Add Input Validation
```python
from werkzeug.security import check_password_hash

def validate_login(username, password):
    if not username or not password:
        return False
    if len(username) > 100 or len(password) > 100:
        return False
    return True
```

---

## Monitoring & Logging

### 1. Add Logging
```python
import logging
from logging.handlers import RotatingFileHandler

if not app.debug:
    file_handler = RotatingFileHandler('app.log', maxBytes=10240000, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
```

### 2. Monitor Error Tracking
- Use Sentry for error tracking
- Use Datadog or New Relic for monitoring

### 3. Health Check Endpoint
```python
@app.route('/health', methods=['GET'])
def health_check():
    try:
        cursor = mysql.connection.cursor()
        cursor.execute('SELECT 1')
        cursor.close()
        return {'status': 'healthy'}, 200
    except:
        return {'status': 'unhealthy'}, 500
```

---

## Scaling Considerations

### 1. Database Optimization
- Add database replication
- Use read replicas
- Implement caching layer (Redis)

### 2. Application Scaling
- Use load balancer (nginx, HAProxy)
- Run multiple Flask instances
- Use CDN for static files

### 3. File Storage
Consider moving file storage to:
- S3 or similar cloud storage
- Separate file server
- CDN with origin pull

---

## Maintenance & Updates

### Regular Tasks
- Backup database daily
- Monitor error logs
- Update dependencies
- Review security patches
- Monitor performance metrics

### Update Process
```bash
# Pull latest changes
git pull origin main

# Update dependencies
pip install -r requirements.txt --upgrade

# Test in staging
python app.py

# Deploy to production
# (using your deployment process)

# Database migrations if needed
# (if schema changes)
```

---

## Troubleshooting Production Issues

### Application Won't Start
1. Check error logs
2. Verify environment variables
3. Test database connection
4. Check port availability

### Slow Performance
1. Check database queries
2. Monitor CPU/memory usage
3. Review error logs
4. Check file sizes

### Database Connection Issues
1. Verify credentials
2. Check MySQL server status
3. Verify network connectivity
4. Check connection limits

---

## Documentation

Keep documentation up-to-date including:
- Deployment procedures
- Rollback procedures
- Emergency contacts
- Architecture diagrams
- Database schema documentation

---

## Support & Resources

- Flask Documentation: https://flask.palletsprojects.com/
- MySQL Documentation: https://dev.mysql.com/doc/
- Gunicorn Documentation: https://gunicorn.org/
- Docker Documentation: https://docs.docker.com/
- Nginx Documentation: https://nginx.org/en/docs/

---

**Last Updated**: November 14, 2025
