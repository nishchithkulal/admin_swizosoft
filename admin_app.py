from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask import send_from_directory, send_file
import pymysql
import pymysql.cursors
import io
from functools import wraps
import admin_app

# Minimal Admin-only Flask app
app = Flask(__name__)

# Load config from existing config.py
from config import get_config
app.config.from_object(get_config())

# Files uploaded path (change via env or config if needed)
UPLOAD_FOLDER = app.config.get('UPLOAD_FOLDER', 'uploads')
# Lightweight health endpoint so the server can be validated without DB access
@app.route('/ping')
def ping():
    return 'pong', 200
# Database connection helper
def get_db():
    """Get database connection"""
    return pymysql.connect(
        host=app.config.get('MYSQL_HOST'),
        user=app.config.get('MYSQL_USER'),
        password=app.config.get('MYSQL_PASSWORD'),
        database=app.config.get('MYSQL_DB'),
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor,
    )

# Admin credentials from config
ADMIN_USERNAME = app.config.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = app.config.get('ADMIN_PASSWORD', 'admin123')

def _resolve_table_name(base_name):
    """Resolve table names: prefer provided base name, fall back to base + '_application'"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        db = app.config.get('MYSQL_DB')
        candidates = [base_name, f"{base_name}_application"]
        for t in candidates:
            cursor.execute(
                "SELECT COUNT(*) AS cnt FROM information_schema.tables WHERE table_schema=%s AND table_name=%s",
                (db, t),
            )
            row = cursor.fetchone()
            # row will be a dict because we use DictCursor
            if row and row.get('cnt', 0) > 0:
                cursor.close()
                conn.close()
                return t
        cursor.close()
        conn.close()
    except Exception:
        pass
    return base_name

# Lazy cache for resolved table names to avoid DB calls at import time
_TABLE_NAME_CACHE = {}
def get_resolved_table(base_name):
    """Resolve and cache table name, but do it lazily to avoid DB calls on import."""
    if base_name in _TABLE_NAME_CACHE:
        return _TABLE_NAME_CACHE[base_name]
    try:
        resolved = _resolve_table_name(base_name)
    except Exception:
        resolved = base_name
    _TABLE_NAME_CACHE[base_name] = resolved
    return resolved

# Simple login-required decorator
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)

    return decorated


@app.route('/')
def root():
    if session.get('admin_logged_in'):
        return redirect(url_for('admin_dashboard'))
    return redirect(url_for('admin_login'))


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            error = 'Invalid username or password'
    return render_template('admin_login.html', error=error)


@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect(url_for('admin_login'))


@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    # Dashboard HTML will fetch data via API
    return render_template('admin_dashboard.html')


@app.route('/admin/api/get-internships')
@login_required
def admin_get_internships():
    """Return details for the dashboard: id, name, usn, id_proof, resume, project_document
       Query param: type=free|paid (default free)
    """
    internship_type = request.args.get('type', 'free')
    try:
        conn = get_db()
        cursor = conn.cursor()
        table = get_resolved_table('paid_internship') if internship_type == 'paid' else get_resolved_table('free_internship')
        # Free table has `project_document`, paid table does not. Use a safe select per type.
        if internship_type == 'paid':
            query = (
                f"SELECT id, name, usn, id_proof, resume, NULL as project_document "
                f"FROM {table} ORDER BY created_at DESC LIMIT 100"
            )
        else:
            query = (
                f"SELECT id, name, usn, id_proof, resume, project_document "
                f"FROM {table} ORDER BY created_at DESC LIMIT 100"
            )

        try:
            cursor.execute(query)
            rows = cursor.fetchall()
        except Exception:
            # try alternate table name (toggle _application suffix)
            alt_table = table + '_application' if not table.endswith('_application') else table.replace('_application', '')
            if internship_type == 'paid':
                alt_query = (
                    f"SELECT id, name, usn, id_proof, resume, NULL as project_document "
                    f"FROM {alt_table} ORDER BY created_at DESC LIMIT 100"
                )
            else:
                alt_query = (
                    f"SELECT id, name, usn, id_proof, resume, project_document "
                    f"FROM {alt_table} ORDER BY created_at DESC LIMIT 100"
                )
            cursor.execute(alt_query)
            rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify({'success': True, 'data': rows})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/admin/api/get-file/<int:internship_id>/<file_type>')
@login_required
def admin_get_file(internship_id, file_type):
    """Get file path from database
       file_type: id_proof, resume, project
       Returns: {file_name: "...", file_type: "..."}
    """
    internship_type = request.args.get('type', 'free')

    column_map = {
        'id_proof': 'id_proof',
        'resume': 'resume',
        'project': 'project_document',
    }

    if file_type not in column_map:
        return jsonify({'error': 'Invalid file type'}), 400

    column = column_map[file_type]

    try:
        conn = get_db()
        cursor = conn.cursor()
        table = get_resolved_table('paid_internship') if internship_type == 'paid' else get_resolved_table('free_internship')
        query = f"SELECT {column} FROM {table} WHERE id = %s"
        try:
            cursor.execute(query, (internship_id,))
            result = cursor.fetchone()
        except Exception:
            alt_table = table + '_application' if not table.endswith('_application') else table.replace('_application', '')
            alt_query = f"SELECT {column} FROM {alt_table} WHERE id = %s"
            cursor.execute(alt_query, (internship_id,))
            result = cursor.fetchone()

        cursor.close()
        conn.close()

        if result and result.get(column):
            file_name = result[column]
            # build URL to serve the file from the uploads folder or external host
            import os
            local_path = os.path.join(app.root_path, UPLOAD_FOLDER, file_name) if isinstance(file_name, str) else None
            if local_path and os.path.exists(local_path):
                file_url = url_for('admin_serve_file', filename=file_name)
            else:
                # try an external base URL (configure via UPLOAD_URL_BASE), fall back to mysql host
                if isinstance(file_name, str) and (file_name.startswith('http://') or file_name.startswith('https://')):
                    file_url = file_name
                else:
                    base = app.config.get('UPLOAD_URL_BASE') or f"https://{app.config.get('MYSQL_HOST')}/uploads"
                    file_url = base.rstrip('/') + '/' + (file_name if isinstance(file_name, str) else '')
            # Also provide an inplace URL which serves the file content for embedding
            try:
                inplace_url = url_for('admin_serve_file_inplace', internship_id=internship_id, file_type=file_type, type=internship_type)
            except Exception:
                inplace_url = file_url
            return jsonify({'success': True, 'file_name': file_name, 'file_type': file_type, 'file_url': file_url, 'inplace_url': inplace_url})
        else:
            return jsonify({'success': False, 'error': 'File not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/admin/files/<path:filename>')
@login_required
def admin_serve_file(filename):
    """Serve uploaded files from UPLOAD_FOLDER for admin access."""
    # Prevent directory traversal by using safe join and send_from_directory
    try:
        import os
        directory = os.path.join(app.root_path, UPLOAD_FOLDER)
        return send_from_directory(directory, filename, as_attachment=False)
    except Exception as e:
        return (f"File not found: {filename}", 404)


@app.route('/admin/serve-file-inplace/<int:internship_id>/<file_type>')
@login_required
def admin_serve_file_inplace(internship_id, file_type):
    """Serve file content inline for viewing in-browser.
       Handles BLOB bytes or filename strings stored in DB.
       Query param: type=free|paid
       file_type: id_proof, resume, project
    """
    internship_type = request.args.get('type', 'free')
    column_map = {
        'id_proof': 'id_proof',
        'resume': 'resume',
        'project': 'project_document',
    }
    if file_type not in column_map:
        return ("Invalid file type", 400)
    column = column_map[file_type]

    try:
        conn = get_db()
        cursor = conn.cursor()
        table = get_resolved_table('paid_internship') if internship_type == 'paid' else get_resolved_table('free_internship')
        query = f"SELECT {column} FROM {table} WHERE id = %s"
        try:
            cursor.execute(query, (internship_id,))
            result = cursor.fetchone()
        except Exception:
            alt_table = table + '_application' if not table.endswith('_application') else table.replace('_application', '')
            alt_query = f"SELECT {column} FROM {alt_table} WHERE id = %s"
            cursor.execute(alt_query, (internship_id,))
            result = cursor.fetchone()

        cursor.close()
        conn.close()

        if not result or not result.get(column):
            return ("File not found", 404)

        value = result[column]

        # If DB stored file as bytes (BLOB)
        if isinstance(value, (bytes, bytearray)):
            data = bytes(value)
            # Detect file type by magic bytes
            mime = 'application/octet-stream'
            if data.startswith(b'%PDF'):
                mime = 'application/pdf'
            elif data.startswith(b'\xff\xd8'):
                mime = 'image/jpeg'
            elif data.startswith(b'\x89PNG'):
                mime = 'image/png'
            return send_file(io.BytesIO(data), mimetype=mime, as_attachment=False)

        # If DB stored a string (filename or URL path)
        if isinstance(value, str):
            import os
            # Check if it's an absolute URL
            if value.startswith('http://') or value.startswith('https://'):
                return redirect(value)

            # Try local file first (relative to UPLOAD_FOLDER)
            local_path = os.path.join(app.root_path, UPLOAD_FOLDER, value)
            if os.path.exists(local_path):
                # Detect extension to set correct mime type
                ext = os.path.splitext(value)[1].lower()
                mime = 'application/octet-stream'
                if ext == '.pdf':
                    mime = 'application/pdf'
                elif ext in ('.jpg', '.jpeg'):
                    mime = 'image/jpeg'
                elif ext == '.png':
                    mime = 'image/png'
                elif ext in ('.docx', '.doc'):
                    mime = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                return send_from_directory(os.path.join(app.root_path, UPLOAD_FOLDER), value, as_attachment=False)

            # Fallback to external base URL
            base = app.config.get('UPLOAD_URL_BASE') or f"https://{app.config.get('MYSQL_HOST')}/uploads"
            external_url = base.rstrip('/') + '/' + value
            return redirect(external_url)

        # Unknown format
        return ("File format not supported", 415)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return (f"Error: {str(e)}", 500)


@app.route('/admin/job-description', methods=['GET', 'POST'])
@login_required
def admin_job_description():
    """Page to view/edit/delete/add the job description stored in the database.
       The code will create a small table `job_description` if it does not exist and
       store a single row with id=1.
    """
    # Work with DB but tolerate missing table or permissions. Provide user-friendly page.
    conn = None
    cursor = None
    description = ''
    try:
        conn = get_db()
        cursor = conn.cursor()

        # Try to ensure table exists, but ignore errors (some hosts may not allow CREATE)
        try:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS job_description (
                    id INT PRIMARY KEY,
                    description TEXT
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
            conn.commit()
        except Exception:
            # Log but continue; we'll handle missing table below
            print('Warning: could not create job_description table (may lack permissions)')

        # Discover columns in the existing table (if any)
        try:
            cursor.execute("SELECT COLUMN_NAME FROM information_schema.columns WHERE table_schema=%s AND table_name=%s ORDER BY ORDINAL_POSITION", (app.config.get('MYSQL_DB'), 'job_description'))
            cols = [r['COLUMN_NAME'] for r in cursor.fetchall()]
        except Exception:
            cols = []

        # pick a sensible description column if present
        desc_col = None
        if cols:
            for candidate in ('description', 'job_description', 'jd', 'text', 'desc'):
                if candidate in cols:
                    desc_col = candidate
                    break
            if not desc_col:
                for c in cols:
                    if c.lower() != 'id':
                        desc_col = c
                        break

        if request.method == 'POST':
            action = request.form.get('action')
            desc = request.form.get('description', '').strip()
            try:
                if not cols:
                    # Try to create default table if it didn't exist
                    try:
                        cursor.execute("CREATE TABLE IF NOT EXISTS job_description (id INT PRIMARY KEY, description TEXT) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4")
                        conn.commit()
                        desc_col = 'description'
                        cols = ['id', 'description']
                    except Exception:
                        pass

                if desc_col == 'description' and 'id' in [c.lower() for c in cols]:
                    # id+description schema
                    cursor.execute("SELECT id FROM job_description WHERE id = 1")
                    if cursor.fetchone():
                        if action in ('save', 'add'):
                            cursor.execute("UPDATE job_description SET description = %s WHERE id = 1", (desc,))
                        elif action == 'delete':
                            cursor.execute("DELETE FROM job_description WHERE id = 1")
                    else:
                        if action in ('save', 'add'):
                            cursor.execute("INSERT INTO job_description (id, description) VALUES (1, %s)", (desc,))
                    conn.commit()
                else:
                    # single-column or unknown schema: update or insert into the detected column
                    if not desc_col and cols:
                        desc_col = cols[0]
                    if desc_col:
                        cursor.execute("SELECT COUNT(*) as cnt FROM job_description")
                        cnt = cursor.fetchone().get('cnt', 0)
                        if action == 'delete':
                            cursor.execute("DELETE FROM job_description")
                        elif cnt == 0:
                            cursor.execute(f"INSERT INTO job_description ({desc_col}) VALUES (%s)", (desc,))
                        else:
                            cursor.execute(f"UPDATE job_description SET {desc_col} = %s", (desc,))
                        conn.commit()
            except Exception as e:
                print('DB write error in admin_job_description:', e)
            return redirect(url_for('admin_job_description'))

        # GET: read the description using detected column
        if cols and desc_col:
            try:
                cursor.execute(f"SELECT {desc_col} FROM job_description LIMIT 1")
                row = cursor.fetchone()
                if row and row.get(desc_col):
                    description = row.get(desc_col)
            except Exception:
                pass

    finally:
        if cursor:
            try:
                cursor.close()
            except Exception:
                pass
        if conn:
            try:
                conn.close()
            except Exception:
                pass

    return render_template('admin_job_description.html', description=description)


# Check what table name is resolved
conn = admin_app.get_db()
cur = conn.cursor()

table = admin_app.get_resolved_table('free_internship')
print(f"Using table: {table}")

# Get a sample row with all file columns
cur.execute(f"SELECT id, name, resume, id_proof, project_document FROM {table} LIMIT 1")
row = cur.fetchone()
print(f"Sample row: {row}")
print(f"Resume type: {type(row['resume']) if row else 'No data'}")
print(f"Resume value: {row['resume'] if row else 'No data'}")

cur.close()
conn.close()

if __name__ == '__main__':
    # Ensure a secret key exists for session support
    if not app.secret_key:
        app.secret_key = app.config.get('SECRET_KEY') or 'dev-secret-change-me'
    # Diagnostic prints to help debugging when the process exits immediately
    try:
        import sys, platform, os
        print('Starting admin_app.py', file=sys.stderr)
        print('Python executable:', sys.executable, file=sys.stderr)
        print('Python version:', sys.version.replace('\n', ' '), file=sys.stderr)
        print('CWD:', os.getcwd(), file=sys.stderr)
        print('App debug:', app.debug, file=sys.stderr)
        print('App secret set:', bool(app.secret_key), file=sys.stderr)
    except Exception:
        pass

    # Show the URL and run the dev server without the reloader so the process
    # you start is the one serving requests (avoids parent process exit visible
    # to some shells when the reloader spawns a child).
    try:
        print('Server listening at http://127.0.0.1:5000', file=sys.stderr)
    except Exception:
        pass
    app.run(host='127.0.0.1', port=5000, debug=app.debug, use_reloader=False)
