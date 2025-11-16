from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask import send_from_directory, send_file
import pymysql
import pymysql.cursors
import io
from functools import wraps
import json
import base64

# Minimal Admin-only Flask app
app = Flask(__name__)

# Load config from existing config.py
from config import get_config
app.config.from_object(get_config())

# Configure SQLAlchemy for approved_candidates
app.config['SQLALCHEMY_DATABASE_URI'] = (
    f"mysql+pymysql://{app.config['MYSQL_USER']}:"
    f"{app.config['MYSQL_PASSWORD']}@"
    f"{app.config['MYSQL_HOST']}/"
    f"{app.config['MYSQL_DB']}"
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Import and initialize SQLAlchemy
from urllib.parse import quote_plus
from models import db, ApprovedCandidate
# URL-encode password to avoid parsing issues when it contains special characters
encoded_pw = quote_plus(app.config.get('MYSQL_PASSWORD', ''))
app.config['SQLALCHEMY_DATABASE_URI'] = (
    f"mysql+pymysql://{app.config.get('MYSQL_USER')}:{encoded_pw}@{app.config.get('MYSQL_HOST')}/{app.config.get('MYSQL_DB')}?charset=utf8mb4"
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# Add connection pooling with better timeout handling
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_size': 10,
    'pool_recycle': 3600,  # Recycle connections every hour
    'pool_pre_ping': True,  # Test connections before using them
    'connect_args': {'connect_timeout': 10}
}
db.init_app(app)

# SMTP / Mail settings (explicitly load per user request)
app.config.update({
    'MAIL_SERVER': 'smtp.hostinger.com',
    'MAIL_PORT': 465,
    'MAIL_USE_SSL': True,
    'MAIL_USERNAME': 'no-reply2@swizosoft.in',
    'MAIL_PASSWORD': 'NOREPLY2@Swizosoft@123...',
    'MAIL_DEFAULT_SENDER': 'no-reply2@swizosoft.in',
})

# Initialize mail (admin_email_sender provides the Mail() instance)
from admin_email_sender import mail, send_accept_email, send_reject_email
mail.init_app(app)

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


# Best-effort: ensure `approved_candidates.job_description` column exists before ORM queries run.
try:
    conn_check = get_db()
    cur_check = conn_check.cursor()
    cur_check.execute("SELECT COLUMN_NAME FROM information_schema.columns WHERE table_schema=%s AND table_name=%s", (app.config.get('MYSQL_DB'), 'approved_candidates'))
    existing = [r['COLUMN_NAME'] for r in cur_check.fetchall()]
    if 'job_description' not in existing:
        try:
            cur_check.execute("ALTER TABLE approved_candidates ADD COLUMN job_description TEXT")
            conn_check.commit()
            print('Ensured approved_candidates.job_description column (added)')
        except Exception as e:
            # Older MySQL versions or permission issues may fail; log and continue
            print('Could not add approved_candidates.job_description at import-time:', e)
    cur_check.close()
    conn_check.close()
except Exception:
    pass

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


@app.route('/admin/selected')
@login_required
def admin_selected():
    return render_template('admin_selected.html')


@app.route('/admin/approved-candidates')
@login_required
def admin_approved_candidates():
    return render_template('admin_approved_candidates.html')


@app.route('/admin/api/get-selected')
@login_required
def admin_api_get_selected():
    """Fetch all rows from Selected table using exact SQL query"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Execute exact query: SELECT * FROM `Selected`
        try:
            cursor.execute('SELECT * FROM `Selected`')
            rows = cursor.fetchall()
            print(f"✓ Fetched {len(rows)} rows from Selected table")
            
            # Convert bytes to base64 strings for JSON serialization
            processed_rows = []
            for row in rows:
                if isinstance(row, dict):
                    processed_row = {}
                    for key, val in row.items():
                        if isinstance(val, bytes):
                            # Convert bytes to base64 string
                            import base64
                            processed_row[key] = base64.b64encode(val).decode('utf-8')
                        else:
                            processed_row[key] = val
                    processed_rows.append(processed_row)
                else:
                    processed_rows.append(row)
            
            if processed_rows:
                print(f"  First row keys: {list(processed_rows[0].keys())}")
                
        except Exception as e:
            print(f"✗ Query failed: {e}")
            processed_rows = []
        
        cursor.close()
        conn.close()
        
        return jsonify({'success': True, 'data': processed_rows})
    except Exception as e:
        print(f"✗ Exception in /admin/api/get-selected: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/admin/api/get-approved-candidates')
@login_required
def admin_api_get_approved_candidates():
    """Fetch all approved candidates from approved_candidates table using SQLAlchemy ORM"""
    max_retries = 3
    retry_count = 0

    import traceback

    # If the admin session is not present, return JSON 401 instead of redirecting (helps AJAX callers)
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401

    while retry_count < max_retries:
        try:
            # Query all approved candidates ordered by created_at descending
            approved_candidates = ApprovedCandidate.query.order_by(ApprovedCandidate.created_at.desc()).all()

            # Convert to list of dictionaries
            processed_rows = []
            for candidate in approved_candidates:
                candidate_dict = candidate.to_dict()

                # Convert BLOB fields to base64 for JSON serialization
                if candidate_dict.get('resume_content') and isinstance(candidate_dict['resume_content'], bytes):
                    candidate_dict['resume_content'] = base64.b64encode(candidate_dict['resume_content']).decode('utf-8')
                if candidate_dict.get('project_document_content') and isinstance(candidate_dict['project_document_content'], bytes):
                    candidate_dict['project_document_content'] = base64.b64encode(candidate_dict['project_document_content']).decode('utf-8')
                if candidate_dict.get('id_proof_content') and isinstance(candidate_dict['id_proof_content'], bytes):
                    candidate_dict['id_proof_content'] = base64.b64encode(candidate_dict['id_proof_content']).decode('utf-8')

                processed_rows.append(candidate_dict)

            # Debug info: print IDs returned
            ids = [c.get('usn') for c in processed_rows]
            print(f"✓ Fetched {len(processed_rows)} approved candidates; USNs: {ids[:10]}")
            return jsonify({'success': True, 'data': processed_rows})
        except Exception as e:
            retry_count += 1
            tb = traceback.format_exc()
            print(f"✗ Exception in /admin/api/get-approved-candidates (attempt {retry_count}/{max_retries}): {str(e)[:200]}")
            print(tb)

            if retry_count < max_retries:
                # Try to reset the connection and retry
                try:
                    db.session.remove()
                    db.session.close()
                except Exception:
                    pass
            else:
                # All retries exhausted — return the exception message to the client (for debugging)
                return jsonify({'success': False, 'error': 'Database error', 'exception': str(e)}), 500


@app.route('/admin/api/get-approved-file/<usn>', methods=['GET'])
@login_required
def admin_api_get_approved_file(usn):
    """Get file for approved candidate (resume, id_proof, or project_document)"""
    file_type = request.args.get('type', 'resume')
    
    if file_type not in ('resume', 'id_proof', 'project'):
        return jsonify({'success': False, 'error': 'Invalid file type'}), 400
    
    try:
        # Query the approved candidate by USN
        approved_candidate = ApprovedCandidate.query.filter_by(usn=usn).first()
        
        if not approved_candidate:
            return jsonify({'success': False, 'error': 'Candidate not found'}), 404
        
        # Map file type to column
        blob_map = {
            'resume': 'resume_content',
            'id_proof': 'id_proof_content',
            'project': 'project_document_content',
        }
        
        column_name = blob_map[file_type]
        blob_content = getattr(approved_candidate, column_name, None)
        
        if not blob_content:
            return jsonify({'success': False, 'error': f'No {file_type} available'}), 404
        
        # Encode BLOB to base64 for JSON transmission
        if isinstance(blob_content, bytes):
            file_data = base64.b64encode(blob_content).decode('utf-8')
        else:
            file_data = blob_content
        
        # Detect file type from magic bytes
        if isinstance(blob_content, bytes):
            data_bytes = blob_content
        else:
            data_bytes = base64.b64decode(file_data)
        
        detected_ext = 'bin'
        if data_bytes.startswith(b'%PDF'):
            detected_ext = 'pdf'
        elif data_bytes.startswith(b'\xff\xd8'):
            detected_ext = 'jpg'
        elif data_bytes.startswith(b'\x89PNG'):
            detected_ext = 'png'
        elif data_bytes.startswith(b'PK\x03\x04'):
            detected_ext = 'docx'
        
        return jsonify({
            'success': True,
            'file_data': file_data,
            'file_type': file_type,
            'file_name': f'{file_type}.{detected_ext}',
            'mime_type': 'application/octet-stream'
        })
    except Exception as e:
        print(f"✗ Exception in /admin/api/get-approved-file: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/admin/api/edit-profile/<int:internship_id>', methods=['PUT'])
@login_required
def admin_edit_profile(internship_id):
    """Edit user profile fields (not files).
       PUT params (JSON body):
       - type: 'free' or 'paid'
       - fields: dict of column_name: value pairs to update
       
       Non-editable fields: reason, applicationid, status, domain, id, file columns, timestamps
       
       Example: PUT /admin/api/edit-profile/123?type=free
       Body: {"name": "John Doe", "usn": "CS123", "email": "john@example.com"}
    """
    internship_type = request.args.get('type', 'free')
    
    try:
        data = request.get_json() or {}
        
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        # Exclude file-related columns and non-editable fields
        excluded_cols = ['id', 'id_proof', 'resume', 'project_document', 'payment_screenshot', 
                        'id_proof_content', 'resume_content', 'project_document_content',
                        'reason', 'applicationid', 'application_id', 'status', 'domain', 'created_at', 'updated_at']
        
        # Build update query
        update_fields = []
        update_values = []
        
        for col, val in data.items():
            if col.lower() not in [c.lower() for c in excluded_cols]:
                update_fields.append(f"{col} = %s")
                update_values.append(val)
        
        if not update_fields:
            return jsonify({'success': False, 'error': 'No valid fields to update'}), 400
        
        update_values.append(internship_id)
        
        conn = get_db()
        cursor = conn.cursor()
        table = get_resolved_table('paid_internship') if internship_type == 'paid' else get_resolved_table('free_internship')
        
        query = f"UPDATE {table} SET {', '.join(update_fields)} WHERE id = %s"
        
        try:
            cursor.execute(query, tuple(update_values))
            conn.commit()
        except Exception:
            # Try alternate table name
            alt_table = table + '_application' if not table.endswith('_application') else table.replace('_application', '')
            alt_query = f"UPDATE {alt_table} SET {', '.join(update_fields)} WHERE id = %s"
            cursor.execute(alt_query, tuple(update_values))
            conn.commit()
        
        cursor.close()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Profile updated successfully'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/admin/api/get-profile/<int:internship_id>', methods=['GET'])
@login_required
def admin_get_profile(internship_id):
    """Get full profile data for editing.
       Query param: type=free|paid
    """
    internship_type = request.args.get('type', 'free')
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        table = get_resolved_table('paid_internship') if internship_type == 'paid' else get_resolved_table('free_internship')
        
        # Get all columns except BLOBs
        query = f"SELECT * FROM {table} WHERE id = %s LIMIT 1"
        
        try:
            cursor.execute(query, (internship_id,))
            result = cursor.fetchone()
        except Exception:
            alt_table = table + '_application' if not table.endswith('_application') else table.replace('_application', '')
            alt_query = f"SELECT * FROM {alt_table} WHERE id = %s LIMIT 1"
            cursor.execute(alt_query, (internship_id,))
            result = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if not result:
            return jsonify({'success': False, 'error': 'Profile not found'}), 404
        
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/admin/api/get-file/<int:internship_id>/<file_type>')
@login_required
def admin_get_file(internship_id, file_type):

    """Get file from database (either from document_store BLOB or application string column)
       file_type: id_proof, resume, project
       Returns: inplace_url to fetch the BLOB
    """
    internship_type = request.args.get('type', 'free')

    blob_column_map = {
        'id_proof': 'id_proof_content',
        'resume': 'resume_content',
        'project': 'project_document_content',
    }

    if file_type not in blob_column_map:
        return jsonify({'error': 'Invalid file type'}), 400

    try:
        # First, try to fetch from document_store (BLOBs)
        conn = get_db()
        cursor = conn.cursor()
        
        # Determine document store table name
        doc_store_table = 'paid_document_store' if internship_type == 'paid' else 'free_document_store'
        app_id_col = 'paid_internship_application_id' if internship_type == 'paid' else 'free_internship_application_id'
        blob_col = blob_column_map[file_type]
        
        try:
            # Try to fetch from document_store
            query = f"SELECT {blob_col} FROM {doc_store_table} WHERE {app_id_col} = %s"
            cursor.execute(query, (internship_id,))
            result = cursor.fetchone()
        except Exception:
            # Try alternate table name or column name
            result = None
        
        cursor.close()
        conn.close()
        
        # If found BLOB in document_store, detect file type and use inplace_url to serve it
        if result and result.get(blob_col):
            data = bytes(result.get(blob_col))
            detected_ext = 'bin'
            
            # Detect file type from magic bytes
            if data.startswith(b'%PDF'):
                detected_ext = 'pdf'
            elif data.startswith(b'\xff\xd8'):
                detected_ext = 'jpg'
            elif data.startswith(b'\x89PNG'):
                detected_ext = 'png'
            elif data.startswith(b'PK\x03\x04'):  # DOCX/XLSX/PPTX
                detected_ext = 'docx'
            
            inplace_url = url_for('admin_serve_file_inplace', internship_id=internship_id, file_type=file_type, type=internship_type)
            return jsonify({'success': True, 'file_name': f'{file_type}.{detected_ext}', 'file_type': file_type, 'inplace_url': inplace_url})
        
        # Fallback: try to get filename from application table
        conn = get_db()
        cursor = conn.cursor()
        table = get_resolved_table('paid_internship') if internship_type == 'paid' else get_resolved_table('free_internship')
        
        column_map = {
            'id_proof': 'id_proof',
            'resume': 'resume',
            'project': 'project_document',
        }
        column = column_map[file_type]
        
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


@app.route('/admin/api/update-status/<int:internship_id>', methods=['POST'])
@login_required
def admin_update_status(internship_id):
    """Update acceptance status (ACCEPTED/REJECTED) for an internship application.
       POST params: status=ACCEPTED|REJECTED, type=free|paid
    """
    internship_type = request.json.get('type', 'free')
    status = request.json.get('status', '').upper()
    
    if status not in ('ACCEPTED', 'REJECTED'):
        return jsonify({'success': False, 'error': 'Invalid status'}), 400
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        table = get_resolved_table('paid_internship') if internship_type == 'paid' else get_resolved_table('free_internship')
        
        # Update the status column (if it exists)
        try:
            query = f"UPDATE {table} SET status = %s WHERE id = %s"
            cursor.execute(query, (status, internship_id))
            conn.commit()
            cursor.close()
            conn.close()
            return jsonify({'success': True, 'message': f'Status updated to {status}'})
        except Exception:
            # Try alternate table name
            alt_table = table + '_application' if not table.endswith('_application') else table.replace('_application', '')
            query = f"UPDATE {alt_table} SET status = %s WHERE id = %s"
            cursor.execute(query, (status, internship_id))
            conn.commit()
            cursor.close()
            conn.close()
            return jsonify({'success': True, 'message': f'Status updated to {status}'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

def _fetch_applicant_contact(internship_id, internship_type='free'):
    """Return (email, name) for given application id and type or (None, None)."""
    conn = None
    cursor = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        table = get_resolved_table('paid_internship') if internship_type == 'paid' else get_resolved_table('free_internship')

        # Discover columns in the actual table
        try:
            cursor.execute("SELECT COLUMN_NAME FROM information_schema.columns WHERE table_schema=%s AND table_name=%s ORDER BY ORDINAL_POSITION", (app.config.get('MYSQL_DB'), table))
            cols = [r['COLUMN_NAME'] for r in cursor.fetchall()]
        except Exception:
            cols = []

        # Map lowercase -> actual name for case-insensitive lookup
        lower_map = {c.lower(): c for c in cols}

        email_col = None
        name_col = None
        for candidate in ('email', 'applicant_email', 'email_address', 'emailid', 'mail'):
            if candidate in lower_map:
                email_col = lower_map[candidate]
                break
        for candidate in ('name', 'full_name', 'applicant_name', 'student_name'):
            if candidate in lower_map:
                name_col = lower_map[candidate]
                break

        # Fallback to any column containing 'email' or 'name'
        if not email_col:
            for c in cols:
                if 'email' in c.lower():
                    email_col = c
                    break
        if not name_col:
            for c in cols:
                if 'name' in c.lower() and 'email' not in c.lower():
                    name_col = c
                    break

        if not email_col and not name_col:
            return (None, None)

        sel_cols = []
        if email_col:
            sel_cols.append(email_col)
        if name_col:
            sel_cols.append(name_col)

        # Build and execute select
        try:
            query = f"SELECT {', '.join(sel_cols)} FROM {table} WHERE id = %s"
            cursor.execute(query, (internship_id,))
            row = cursor.fetchone()
        except Exception:
            # Try alternate table name
            alt_table = table + '_application' if not table.endswith('_application') else table.replace('_application', '')
            try:
                query = f"SELECT {', '.join(sel_cols)} FROM {alt_table} WHERE id = %s"
                cursor.execute(query, (internship_id,))
                row = cursor.fetchone()
            except Exception:
                row = None

        if not row:
            return (None, None)

        email = None
        name = None
        if email_col:
            email = row.get(email_col)
        if name_col:
            name = row.get(name_col)

        return (email, name)
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

@app.route('/accept/<int:user_id>', methods=['POST'])
@login_required
def admin_accept(user_id):
    internship_type = request.args.get('type', 'free')
    email, name = _fetch_applicant_contact(user_id, internship_type)
    if not email:
        return jsonify({'success': False, 'error': 'Applicant email not found'}), 404

    # details to include in accept email (populated for free internships)
    details_for_email = None
    # Update status in DB (best-effort)
    try:
        conn = get_db()
        cursor = conn.cursor()
        table = get_resolved_table('paid_internship') if internship_type == 'paid' else get_resolved_table('free_internship')
        try:
            cursor.execute(f"UPDATE {table} SET status = %s WHERE id = %s", ('ACCEPTED', user_id))
            conn.commit()
        except Exception:
            alt = table + '_application' if not table.endswith('_application') else table.replace('_application', '')
            try:
                cursor.execute(f"UPDATE {alt} SET status = %s WHERE id = %s", ('ACCEPTED', user_id))
                conn.commit()
            except Exception:
                pass
        cursor.close()
        conn.close()
    except Exception:
        pass

    # Track whether we inserted into Selected (for paid internships)
    selected_inserted = None
    selected_insert_error = None

    # If this is a paid internship, store the full applicant details in the Selected table
    if internship_type == 'paid':
        try:
            conn = get_db()
            cursor = conn.cursor()
            paid_table = get_resolved_table('paid_internship')
            
            # Fetch applicant row
            row = None
            try:
                cursor.execute(f"SELECT * FROM {paid_table} WHERE id = %s LIMIT 1", (user_id,))
                row = cursor.fetchone()
            except Exception as e:
                alt_table = paid_table.replace('_application', '') if paid_table.endswith('_application') else paid_table + '_application'
                try:
                    cursor.execute(f"SELECT * FROM {alt_table} WHERE id = %s LIMIT 1", (user_id,))
                    row = cursor.fetchone()
                except Exception:
                    pass

            if row:
                # Extract basic info
                row_map = {k.lower(): v for k, v in (row.items() if isinstance(row, dict) else [])}
                
                application_id = user_id
                name_val = row_map.get('name') or row_map.get('full_name') or ''
                email_val = row_map.get('email') or row_map.get('applicant_email') or ''
                phone_val = row_map.get('phone') or row_map.get('mobile') or row_map.get('contact_number') or ''
                usn_val = row_map.get('usn') or row_map.get('roll') or ''
                year_val = row_map.get('year') or row_map.get('sem') or ''
                qualification_val = row_map.get('qualification') or ''
                branch_val = row_map.get('branch') or row_map.get('department') or ''
                college_val = row_map.get('college') or ''
                domain_val = row_map.get('domain') or ''
                project_description_val = row_map.get('project_description') or ''
                project_name_val = row_map.get('project_document') or row_map.get('project_name') or ''
                internship_duration_val = row_map.get('internship_duration') or '1 month'
                
                # Fetch document BLOBs
                project_blob = None
                try:
                    cursor.execute(
                        "SELECT project_document_content FROM paid_document_store WHERE paid_internship_application_id = %s LIMIT 1",
                        (user_id,)
                    )
                    blob_row = cursor.fetchone()
                    if blob_row:
                        if isinstance(blob_row, dict):
                            project_blob = blob_row.get('project_document_content')
                        else:
                            project_blob = blob_row[0]
                except Exception:
                    pass
                
                # Insert into Selected table (USN is treated as primary key; avoid duplicates)
                try:
                    inserted = False

                    if not usn_val:
                        app.logger.error(f"Cannot insert paid applicant {user_id} ({name_val}) into Selected: missing USN")
                    else:
                        # Check if USN already exists in Selected (USN is primary key)
                        cursor.execute("SELECT usn FROM Selected WHERE usn = %s LIMIT 1", (usn_val,))
                        exists = cursor.fetchone()

                        if exists:
                            # USN already exists: update the existing Selected record (upsert behavior)
                            try:
                                update_sql = """UPDATE Selected SET
                                    application_id = %s,
                                    name = %s,
                                    email = %s,
                                    phone = %s,
                                    year = %s,
                                    qualification = %s,
                                    branch = %s,
                                    college = %s,
                                    domain = %s,
                                    project_description = %s,
                                    internship_project_name = %s,
                                    internship_project_content = %s,
                                    project_title = %s,
                                    internship_duration = %s,
                                    approved_date = CURDATE(),
                                    status = 'ongoing',
                                    completion_date = CURDATE()
                                    WHERE usn = %s"""

                                cursor.execute(update_sql, (
                                    application_id, name_val, email_val, phone_val,
                                    year_val, qualification_val, branch_val, college_val, domain_val,
                                    project_description_val, project_name_val, project_blob, project_name_val,
                                    internship_duration_val, usn_val
                                ))
                                conn.commit()
                                inserted = True
                                app.logger.info(f"Updated existing Selected record for USN {usn_val} (applicant {user_id} - {name_val})")
                            except Exception as e:
                                app.logger.error(f"Failed to update existing Selected record for USN {usn_val}: {e}")
                                # fall through with inserted False
                        else:
                            insert_sql = """INSERT INTO Selected 
                            (application_id, name, email, phone, usn, year, qualification, branch, college, domain, 
                             project_description, internship_project_name, internship_project_content, project_title, internship_duration)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""

                            cursor.execute(insert_sql, (
                                application_id, name_val, email_val, phone_val, usn_val, year_val,
                                qualification_val, branch_val, college_val, domain_val,
                                project_description_val, project_name_val, project_blob, project_name_val,
                                internship_duration_val
                            ))
                            conn.commit()
                            inserted = True
                            app.logger.info(f"Successfully inserted paid applicant {user_id} ({name_val}) into Selected (USN: {usn_val})")

                    # Now delete original records ONLY if we inserted successfully
                    if inserted:
                        try:
                            cursor.execute("DELETE FROM paid_document_store WHERE paid_internship_application_id = %s", (user_id,))
                            conn.commit()
                        except Exception as e:
                            app.logger.warning(f"Could not delete documents: {e}")

                        try:
                            cursor.execute(f"DELETE FROM {paid_table} WHERE id = %s", (user_id,))
                            conn.commit()
                            app.logger.info(f"Deleted original paid application for {user_id}")
                        except Exception:
                            alt_table = paid_table.replace('_application', '') if paid_table.endswith('_application') else paid_table + '_application'
                            try:
                                cursor.execute(f"DELETE FROM {alt_table} WHERE id = %s", (user_id,))
                                conn.commit()
                            except Exception as e:
                                app.logger.warning(f"Could not delete from {alt_table}: {e}")
                            
                except Exception as e:
                    app.logger.error(f"Error inserting/deleting paid applicant {user_id}: {e}")
                    selected_insert_error = str(e)
                    try:
                        conn.rollback()
                    except Exception:
                        pass
                finally:
                    # reflect insertion outcome
                    selected_inserted = bool(inserted)
            else:
                app.logger.error(f"Could not find paid applicant {user_id}")
            
            cursor.close()
            conn.close()
        except Exception as e:
            app.logger.exception(f"Error processing paid internship for {user_id}: {e}")

    elif internship_type == 'free':
        try:
            conn = get_db()
            cursor = conn.cursor()
            free_table = get_resolved_table('free_internship')
            
            # Fetch full row from free internship table
            row = None
            try:
                cursor.execute(f"SELECT * FROM {free_table} WHERE id = %s LIMIT 1", (user_id,))
                row = cursor.fetchone()
            except Exception:
                alt_table = free_table + '_application' if not free_table.endswith('_application') else free_table.replace('_application', '')
                try:
                    cursor.execute(f"SELECT * FROM {alt_table} WHERE id = %s LIMIT 1", (user_id,))
                    row = cursor.fetchone()
                except Exception:
                    row = None
            
            # If we have a row, try to fetch file BLOBs from free_document_store
            # Filenames come from the free_internship_application row
            resume_blob = None
            project_blob = None
            id_proof_blob = None
            resume_name = None
            project_document_name = None
            id_proof_name = None
            
            if row:
                # First, get filenames from the application row itself
                row_map = {k.lower(): v for k, v in (row.items() if isinstance(row, dict) else [])}
                resume_name = row_map.get('resume')
                project_document_name = row_map.get('project_document')
                id_proof_name = row_map.get('id_proof')
                
                # Now fetch BLOB content from free_document_store
                try:
                    cursor.execute(
                        "SELECT resume_content, project_document_content, id_proof_content FROM free_document_store WHERE free_internship_application_id = %s LIMIT 1",
                        (user_id,)
                    )
                    blob_row = cursor.fetchone()
                    if blob_row:
                        if isinstance(blob_row, dict):
                            resume_blob = blob_row.get('resume_content')
                            project_blob = blob_row.get('project_document_content')
                            id_proof_blob = blob_row.get('id_proof_content')
                        else:
                            # tuple fallback: map by position
                            try:
                                resume_blob = blob_row[0]
                            except Exception:
                                resume_blob = None
                            try:
                                project_blob = blob_row[1]
                            except Exception:
                                project_blob = None
                            try:
                                id_proof_blob = blob_row[2]
                            except Exception:
                                id_proof_blob = None
                except Exception as e:
                    # If query fails, continue with None values
                    app.logger.warning(f"Could not fetch document BLOBs: {e}")
            
            cursor.close()
            conn.close()
            
            # Create and insert ApprovedCandidate record using SQLAlchemy
            approved_inserted = False
            if row:
                try:
                    # Map source columns to ApprovedCandidate fields
                    row_map = {k.lower(): v for k, v in (row.items() if isinstance(row, dict) else [])}
                    
                    # Extract values with fallback logic
                    def get_field(keys, default=None):
                        for key in keys:
                            if key.lower() in row_map:
                                return row_map[key.lower()]
                        return default
                    
                    # Check if already exists
                    usn_val = get_field(['usn', 'roll', 'rollno'])
                    if usn_val:
                        existing = ApprovedCandidate.query.filter_by(usn=usn_val).first()
                        if not existing:
                            # Get application_id from the row
                            app_id = get_field(['application_id'], str(user_id))
                            
                            # Create new approved candidate
                            approved_candidate = ApprovedCandidate(
                                usn=usn_val,
                                application_id=app_id,
                                user_id=user_id,
                                name=get_field(['name', 'full_name', 'applicant_name'], ''),
                                email=get_field(['email', 'applicant_email'], ''),
                                phone_number=get_field(['phone', 'mobile', 'phone_number', 'contact'], ''),
                                year=get_field(['year', 'sem', 'semester', 'batch'], ''),
                                qualification=get_field(['qualification', 'degree'], ''),
                                branch=get_field(['branch', 'department', 'stream'], ''),
                                college=get_field(['college', 'institution', 'institute'], ''),
                                domain=get_field(['domain'], ''),
                                mode_of_interview=get_field(['mode_of_interview', 'interview_mode'], 'online'),
                                resume_name=resume_name,
                                resume_content=resume_blob,
                                project_document_name=project_document_name,
                                project_document_content=project_blob,
                                id_proof_name=id_proof_name,
                                id_proof_content=id_proof_blob
                            )
                            
                            db.session.add(approved_candidate)
                            db.session.commit()
                            approved_inserted = True
                            app.logger.info(f"Successfully inserted free applicant {user_id} ({usn_val}) into approved_candidates")
                            
                            # Prepare details for email (use human-friendly keys)
                            details_for_email = {
                                'application_id': row_map.get('application_id') or user_id,
                                'usn': usn_val,
                                'name': row_map.get('name') or row_map.get('full_name') or '',
                                'email': row_map.get('email') or '',
                                'phone': row_map.get('phone') or row_map.get('mobile') or row_map.get('phone_number') or '',
                                'year': row_map.get('year') or '',
                                'qualification': row_map.get('qualification') or '',
                                'branch': row_map.get('branch') or '',
                                'college': row_map.get('college') or '',
                                'domain': row_map.get('domain') or '',
                                'mode_of_interview': row_map.get('mode_of_interview') or row_map.get('interview_mode') or 'online'
                            }
                            
                            # Delete from free_internship_application and free_document_store only if insertion successful
                            if approved_inserted:
                                try:
                                    # Delete from free_document_store
                                    conn = get_db()
                                    cursor = conn.cursor()
                                    cursor.execute("DELETE FROM free_document_store WHERE free_internship_application_id = %s", (user_id,))
                                    conn.commit()
                                    app.logger.info(f"Deleted documents for free applicant {user_id}")
                                except Exception as e:
                                    app.logger.warning(f"Could not delete documents for free applicant {user_id}: {e}")
                                
                                try:
                                    # Delete from free_internship_application
                                    conn = get_db()
                                    cursor = conn.cursor()
                                    cursor.execute(f"DELETE FROM {free_table} WHERE id = %s", (user_id,))
                                    conn.commit()
                                    app.logger.info(f"Deleted free application for {user_id}")
                                except Exception:
                                    alt_table = free_table.replace('_application', '') if free_table.endswith('_application') else free_table + '_application'
                                    try:
                                        conn = get_db()
                                        cursor = conn.cursor()
                                        cursor.execute(f"DELETE FROM {alt_table} WHERE id = %s", (user_id,))
                                        conn.commit()
                                    except Exception as e:
                                        app.logger.warning(f"Could not delete from {alt_table}: {e}")
                except Exception as e:
                    app.logger.error(f"Error inserting approved candidate: {str(e)}")
                    try:
                        db.session.rollback()
                    except Exception:
                        pass
        except Exception:
            pass

    # If free internship, add interview scheduler link (but do not include report_link in email)
    interview_link = None
    if internship_type == 'free':
        if details_for_email is None:
            details_for_email = {}
        # NOTE: intentionally do NOT add a `report_link` into `details_for_email` to avoid showing it in the email
        interview_link = 'http://127.0.0.1:5000/interview-scheduler'

    ok = send_accept_email(email, name or '', details=details_for_email, interview_link=interview_link, internship_type=internship_type)
    resp = {'success': bool(ok)}
    if ok:
        resp['message'] = 'Accept email sent'
    else:
        resp['error'] = 'Failed to send email'

    # Include Selected insertion result when processing paid internships
    if internship_type == 'paid':
        resp['selected_inserted'] = selected_inserted
        if selected_insert_error:
            resp['selected_insert_error'] = selected_insert_error

    status_code = 200 if ok else 500
    return jsonify(resp), status_code

@app.route('/reject/<int:user_id>', methods=['POST'])
@login_required
def admin_reject(user_id):
    """Reject an internship application: delete all candidate data and documents completely."""
    internship_type = request.args.get('type', 'free')
    reason = request.form.get('reason', '') or request.get_json().get('reason', '') if request.is_json else request.form.get('reason', '')
    
    email, name = _fetch_applicant_contact(user_id, internship_type)
    if not email:
        return jsonify({'success': False, 'error': 'Applicant email not found'}), 404

    # Delete all candidate data and documents from database
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Determine table names based on internship type
        if internship_type == 'paid':
            app_table = get_resolved_table('paid_internship')
            doc_store_table = 'paid_document_store'
        else:
            app_table = get_resolved_table('free_internship')
            doc_store_table = 'free_document_store'
        
        # Try to delete from document store first (by application ID foreign key)
        try:
            if internship_type == 'paid':
                cursor.execute(f"DELETE FROM {doc_store_table} WHERE paid_internship_application_id = %s", (user_id,))
            else:
                cursor.execute(f"DELETE FROM {doc_store_table} WHERE free_internship_application_id = %s", (user_id,))
            conn.commit()
        except Exception as e:
            app.logger.warning(f"Could not delete from {doc_store_table}: {e}")
        
        # Delete from application table
        try:
            cursor.execute(f"DELETE FROM {app_table} WHERE id = %s", (user_id,))
            conn.commit()
        except Exception as e:
            # Try alternate table name
            app.logger.warning(f"Could not delete from {app_table}: {e}")
            alt_table = app_table + '_application' if not app_table.endswith('_application') else app_table.replace('_application', '')
            try:
                cursor.execute(f"DELETE FROM {alt_table} WHERE id = %s", (user_id,))
                conn.commit()
            except Exception as e2:
                app.logger.error(f"Could not delete from {alt_table}: {e2}")
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'error': 'Failed to delete application record'}), 500
        
        cursor.close()
        conn.close()
    except Exception as e:
        app.logger.error(f"Database error during rejection: {e}")
        return jsonify({'success': False, 'error': 'Database error during deletion'}), 500

    # Send rejection email to applicant
    ok = send_reject_email(email, name or '', reason, internship_type=internship_type)
    if ok:
        return jsonify({'success': True, 'message': 'Application rejected and all data deleted. Rejection email sent'})
    else:
        return jsonify({'success': False, 'error': 'Failed to send rejection email'}), 500


@app.route('/admin/api/get-rejection-reasons')
@login_required
def admin_api_get_rejection_reasons():
    """Get list of rejection reasons"""
    reasons = [
        'Does not meet minimum qualifications',
        'Lack of relevant experience',
        'Poor communication skills',
        'Scheduling conflict',
        'Position filled',
        'Insufficient knowledge in required technologies',
        'Cultural fit concerns',
        'Limited availability',
        'Application incomplete',
        'Better candidates available',
        'Technical assessment score below threshold',
        'Interview performance unsatisfactory',
        'Not meeting location requirements',
        'Salary expectations mismatch',
        'Background check issues',
        'Duplicate application',
        'Falsified credentials or information',
        'Unable to relocate',
        'Visa sponsorship not available',
        'Minimum GPA requirement not met',
        'Previous negative reference',
        'Insufficient project portfolio',
        'Failed coding test',
        'Attendance concerns',
        'Overqualified for the position',
        'Failed to attend interview',
        'No show on interview day',
        'Poor GitHub profile or code quality',
        'Weak problem-solving skills',
        'Does not meet domain expertise',
        'Behavioral red flags',
        'Not aligned with company values',
        'Budget constraints',
        'Internship role cancelled',
        'Team capacity full',
        'Other'
    ]
    return jsonify({'success': True, 'reasons': reasons})


@app.route('/admin/api/get-payment-screenshots/<int:internship_id>')
@login_required
def admin_get_payment_screenshots(internship_id):
    """Get payment screenshot file path from database (paid internship only).
       Query param: type=free|paid
       Returns: {file_name: "...", inplace_url: "..."}
    """
    internship_type = request.args.get('type', 'paid')
    
    if internship_type != 'paid':
        return jsonify({'success': False, 'error': 'Payment screenshots only available for paid internships'}), 400
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        table = get_resolved_table('paid_internship')
        
        # Assume column is named 'payment_screenshot' or similar
        query = f"SELECT payment_screenshot FROM {table} WHERE id = %s"
        try:
            cursor.execute(query, (internship_id,))
            result = cursor.fetchone()
        except Exception:
            # Try alternate names or table
            alt_table = table + '_application' if not table.endswith('_application') else table.replace('_application', '')
            alt_query = f"SELECT payment_screenshot FROM {alt_table} WHERE id = %s"
            try:
                cursor.execute(alt_query, (internship_id,))
                result = cursor.fetchone()
            except Exception:
                # Try 'payment_proof' instead
                alt_query = f"SELECT payment_proof FROM {alt_table} WHERE id = %s"
                cursor.execute(alt_query, (internship_id,))
                result = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if not result or not result.get('payment_screenshot'):
            # Try payment_proof column
            conn = get_db()
            cursor = conn.cursor()
            try:
                query = f"SELECT payment_proof FROM {table} WHERE id = %s"
                cursor.execute(query, (internship_id,))
                result = cursor.fetchone()
            except Exception:
                pass
            cursor.close()
            conn.close()
            
            if not result or not result.get('payment_proof'):
                return jsonify({'success': False, 'error': 'Payment screenshot not found'}), 404
        
        file_name = result.get('payment_screenshot') or result.get('payment_proof')
        if not file_name:
            return jsonify({'success': False, 'error': 'Payment screenshot not found'}), 404
        
        # Build inplace URL to display the screenshot
        inplace_url = url_for('admin_serve_file_inplace', internship_id=internship_id, file_type='payment', type='paid')
        return jsonify({'success': True, 'file_name': file_name, 'inplace_url': inplace_url})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/admin/view-file/<int:internship_id>/<file_type>')
@login_required
def admin_view_file(internship_id, file_type):
    """Display file in a separate page with download button in top-right."""
    internship_type = request.args.get('type', 'free')
    
    if file_type not in ('id_proof', 'resume', 'project', 'payment'):
        return ("Invalid file type", 400)
    
    try:
        # Get file info
        conn = get_db()
        cursor = conn.cursor()
        
        # First, try document_store for BLOBs
        filename = None
        detected_ext = 'bin'
        
        if file_type != 'payment':
            doc_store_table = 'paid_document_store' if internship_type == 'paid' else 'free_document_store'
            app_id_col = 'paid_internship_application_id' if internship_type == 'paid' else 'free_internship_application_id'
            
            blob_column_map = {
                'id_proof': 'id_proof_content',
                'resume': 'resume_content',
                'project': 'project_document_content',
            }
            blob_col = blob_column_map.get(file_type)
            
            if blob_col:
                try:
                    query = f"SELECT {blob_col} FROM {doc_store_table} WHERE {app_id_col} = %s"
                    cursor.execute(query, (internship_id,))
                    result = cursor.fetchone()
                    if result and result.get(blob_col):
                        data = bytes(result.get(blob_col))
                        
                        if data.startswith(b'%PDF'):
                            detected_ext = 'pdf'
                        elif data.startswith(b'\xff\xd8'):
                            detected_ext = 'jpg'
                        elif data.startswith(b'\x89PNG'):
                            detected_ext = 'png'
                        elif data.startswith(b'PK\x03\x04'):
                            detected_ext = 'docx'
                        
                        filename = f'{file_type}.{detected_ext}'
                except Exception:
                    pass
        
        cursor.close()
        conn.close()
        
        if not filename:
            filename = f'{file_type}.bin'
        
        # Build the download URL
        download_url = url_for('admin_serve_file_inplace', internship_id=internship_id, file_type=file_type, type=internship_type)
        file_view_url = url_for('admin_serve_file_inplace', internship_id=internship_id, file_type=file_type, type=internship_type)
        
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{filename} - Swizosoft</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #f5f5f5;
        }}
        
        .viewer-container {{
            display: flex;
            flex-direction: column;
            height: 100vh;
        }}
        
        .viewer-header {{
            background: white;
            padding: 15px 20px;
            border-bottom: 1px solid #ddd;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        
        .viewer-title {{
            font-size: 18px;
            font-weight: 600;
            color: #333;
            flex: 1;
        }}
        
        .download-btn {{
            background: #28a745;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 600;
            transition: background 0.3s ease;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 8px;
        }}
        
        .download-btn:hover {{
            background: #218838;
        }}
        
        .viewer-content {{
            flex: 1;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
            overflow: auto;
            background: #fff;
        }}
        
        .viewer-content img {{
            max-width: 100%;
            max-height: 100%;
            object-fit: contain;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        
        .viewer-content iframe {{
            width: 100%;
            height: 100%;
            border: none;
            border-radius: 8px;
        }}
        
        .loading {{
            text-align: center;
            color: #666;
        }}
    </style>
</head>
<body>
    <div class="viewer-container">
        <div class="viewer-header">
            <div class="viewer-title">{filename}</div>
            <a href="{download_url}?download=1" class="download-btn" download="{filename}">
                ⬇️ Download
            </a>
        </div>
        <div class="viewer-content" id="viewerContent">
            <div class="loading">Loading document...</div>
        </div>
    </div>
    
    <script>
        const filename = "{filename}";
        const fileViewUrl = "{file_view_url}";
        const container = document.getElementById('viewerContent');
        
        // Determine file type from extension
        const ext = filename.split('.').pop().toLowerCase();
        
        if (ext === 'pdf') {{
            const iframe = document.createElement('iframe');
            iframe.src = fileViewUrl;
            container.innerHTML = '';
            container.appendChild(iframe);
        }} else if (['jpg', 'jpeg', 'png', 'gif', 'bmp'].includes(ext)) {{
            const img = document.createElement('img');
            img.src = fileViewUrl;
            img.onload = function() {{
                container.innerHTML = '';
                container.appendChild(img);
            }};
            img.onerror = function() {{
                container.innerHTML = '<div class="loading">Error loading image</div>';
            }};
        }} else if (['docx', 'xlsx', 'pptx'].includes(ext)) {{
            const encodedUrl = encodeURIComponent(fileViewUrl);
            const viewerUrl = 'https://docs.google.com/gview?url=' + encodedUrl + '&embedded=true';
            const iframe = document.createElement('iframe');
            iframe.src = viewerUrl;
            container.innerHTML = '';
            container.appendChild(iframe);
        }} else {{
            const iframe = document.createElement('iframe');
            iframe.src = fileViewUrl;
            container.innerHTML = '';
            container.appendChild(iframe);
        }}
    </script>
</body>
</html>
"""
        return html_content
    except Exception as e:
        return f"Error: {str(e)}", 500


@app.route('/admin/serve-file-inplace/<int:internship_id>/<file_type>')
@login_required
def admin_serve_file_inplace(internship_id, file_type):

    """Serve file content inline for viewing in-browser.
       Tries document_store (BLOBs) first, then falls back to filenames or URLs.
       Query param: type=free|paid, download=1 (to force download)
       file_type: id_proof, resume, project, payment
    """
    internship_type = request.args.get('type', 'free')
    force_download = request.args.get('download', '0') == '1'
    
    if file_type not in ('id_proof', 'resume', 'project', 'payment'):
        return ("Invalid file type", 400)

    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # First, try document_store for BLOBs
        if file_type != 'payment':
            doc_store_table = 'paid_document_store' if internship_type == 'paid' else 'free_document_store'
            app_id_col = 'paid_internship_application_id' if internship_type == 'paid' else 'free_internship_application_id'
            
            blob_column_map = {
                'id_proof': 'id_proof_content',
                'resume': 'resume_content',
                'project': 'project_document_content',
            }
            blob_col = blob_column_map.get(file_type)
            
            if blob_col:
                try:
                    query = f"SELECT {blob_col} FROM {doc_store_table} WHERE {app_id_col} = %s"
                    cursor.execute(query, (internship_id,))
                    result = cursor.fetchone()
                    if result and result.get(blob_col):
                        data = bytes(result.get(blob_col))
                        mime = 'application/octet-stream'
                        filename = f'{file_type}.bin'
                        
                        if data.startswith(b'%PDF'):
                            mime = 'application/pdf'
                            filename = f'{file_type}.pdf'
                        elif data.startswith(b'\xff\xd8'):
                            mime = 'image/jpeg'
                            filename = f'{file_type}.jpg'
                        elif data.startswith(b'\x89PNG'):
                            mime = 'image/png'
                            filename = f'{file_type}.png'
                        elif data.startswith(b'PK\x03\x04'):  # DOCX/XLSX magic bytes
                            mime = 'application/octet-stream'
                            filename = f'{file_type}.docx'
                        
                        cursor.close()
                        conn.close()
                        
                        # Return with appropriate headers
                        from flask import make_response
                        response = make_response(data)
                        response.headers['Content-Type'] = mime
                        if force_download:
                            response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
                        else:
                            response.headers['Content-Disposition'] = 'inline'
                        response.headers['Cache-Control'] = 'public, max-age=3600'
                        return response
                except Exception:
                    pass
        
        # Fallback: try application table (filenames or URLs)
        table = get_resolved_table('paid_internship') if internship_type == 'paid' else get_resolved_table('free_internship')
        
        column_map = {
            'id_proof': 'id_proof',
            'resume': 'resume',
            'project': 'project_document',
            'payment': 'payment_screenshot',
        }
        column = column_map.get(file_type, file_type)
        
        query = f"SELECT {column} FROM {table} WHERE id = %s"
        try:
            cursor.execute(query, (internship_id,))
            result = cursor.fetchone()
        except Exception:
            if file_type == 'payment':
                # Try payment_proof for payment files
                try:
                    query = f"SELECT payment_proof FROM {table} WHERE id = %s"
                    cursor.execute(query, (internship_id,))
                    result = cursor.fetchone()
                except Exception:
                    result = None
            else:
                result = None

        if not result:
            alt_table = table + '_application' if not table.endswith('_application') else table.replace('_application', '')
            try:
                query = f"SELECT {column} FROM {alt_table} WHERE id = %s"
                cursor.execute(query, (internship_id,))
                result = cursor.fetchone()
            except Exception:
                result = None

        cursor.close()
        conn.close()

        if not result:
            return ("File not found", 404)
        
        # Get the value (try column or payment_proof)
        value = result.get(column) or result.get('payment_proof') or result.get('payment_screenshot')
        if not value:
            return ("File not found", 404)

        # If DB stored file as bytes (BLOB)
        if isinstance(value, (bytes, bytearray)):
            data = bytes(value)
            mime = 'application/octet-stream'
            filename = f'{file_type}.bin'
            
            if data.startswith(b'%PDF'):
                mime = 'application/pdf'
                filename = f'{file_type}.pdf'
            elif data.startswith(b'\xff\xd8'):
                mime = 'image/jpeg'
                filename = f'{file_type}.jpg'
            elif data.startswith(b'\x89PNG'):
                mime = 'image/png'
                filename = f'{file_type}.png'
            elif data.startswith(b'PK\x03\x04'):  # DOCX/XLSX
                mime = 'application/octet-stream'
                filename = f'{file_type}.docx'
            
            # Return with appropriate headers
            from flask import make_response
            response = make_response(data)
            response.headers['Content-Type'] = mime
            if force_download:
                response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
            else:
                response.headers['Content-Disposition'] = 'inline'
            response.headers['Cache-Control'] = 'public, max-age=3600'
            return response

        # If DB stored a string (filename or URL path)
        if isinstance(value, str):
            import os
            if value.startswith('http://') or value.startswith('https://'):
                return redirect(value)

            local_path = os.path.join(app.root_path, UPLOAD_FOLDER, value)
            if os.path.exists(local_path):
                ext = os.path.splitext(value)[1].lower()
                mime = 'application/octet-stream'
                if ext == '.pdf':
                    mime = 'application/pdf'
                elif ext in ('.jpg', '.jpeg'):
                    mime = 'image/jpeg'
                elif ext == '.png':
                    mime = 'image/png'
                if force_download:
                    return send_from_directory(os.path.join(app.root_path, UPLOAD_FOLDER), value, as_attachment=True)
                else:
                    return send_from_directory(os.path.join(app.root_path, UPLOAD_FOLDER), value, as_attachment=False)

            base = app.config.get('UPLOAD_URL_BASE') or f"https://{app.config.get('MYSQL_HOST')}/uploads"
            external_url = base.rstrip('/') + '/' + value
            return redirect(external_url)

        return ("File format not supported", 415)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return (f"Error: {str(e)}", 500)
    
    if file_type not in ('id_proof', 'resume', 'project', 'payment'):
        return ("Invalid file type", 400)

    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # First, try document_store for BLOBs
        if file_type != 'payment':
            doc_store_table = 'paid_document_store' if internship_type == 'paid' else 'free_document_store'
            app_id_col = 'paid_internship_application_id' if internship_type == 'paid' else 'free_internship_application_id'
            
            blob_column_map = {
                'id_proof': 'id_proof_content',
                'resume': 'resume_content',
                'project': 'project_document_content',
            }
            blob_col = blob_column_map.get(file_type)
            
            if blob_col:
                try:
                    query = f"SELECT {blob_col} FROM {doc_store_table} WHERE {app_id_col} = %s"
                    cursor.execute(query, (internship_id,))
                    result = cursor.fetchone()
                    if result and result.get(blob_col):
                        data = bytes(result.get(blob_col))
                        mime = 'application/octet-stream'
                        if data.startswith(b'%PDF'):
                            mime = 'application/pdf'
                        elif data.startswith(b'\xff\xd8'):
                            mime = 'image/jpeg'
                        elif data.startswith(b'\x89PNG'):
                            mime = 'image/png'
                        elif data.startswith(b'PK\x03\x04'):  # DOCX/XLSX magic bytes
                            if b'word' in data[:1000]:
                                mime = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                            else:
                                mime = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                        cursor.close()
                        conn.close()
                        return send_file(io.BytesIO(data), mimetype=mime, as_attachment=False)
                except Exception:
                    pass
        
        # Fallback: try application table (filenames or URLs)
        table = get_resolved_table('paid_internship') if internship_type == 'paid' else get_resolved_table('free_internship')
        
        column_map = {
            'id_proof': 'id_proof',
            'resume': 'resume',
            'project': 'project_document',
            'payment': 'payment_screenshot',
        }
        column = column_map.get(file_type, file_type)
        
        query = f"SELECT {column} FROM {table} WHERE id = %s"
        try:
            cursor.execute(query, (internship_id,))
            result = cursor.fetchone()
        except Exception:
            if file_type == 'payment':
                # Try payment_proof for payment files
                try:
                    query = f"SELECT payment_proof FROM {table} WHERE id = %s"
                    cursor.execute(query, (internship_id,))
                    result = cursor.fetchone()
                except Exception:
                    result = None
            else:
                result = None

        if not result:
            alt_table = table + '_application' if not table.endswith('_application') else table.replace('_application', '')
            try:
                query = f"SELECT {column} FROM {alt_table} WHERE id = %s"
                cursor.execute(query, (internship_id,))
                result = cursor.fetchone()
            except Exception:
                result = None

        cursor.close()
        conn.close()

        if not result:
            return ("File not found", 404)
        
        # Get the value (try column or payment_proof)
        value = result.get(column) or result.get('payment_proof') or result.get('payment_screenshot')
        if not value:
            return ("File not found", 404)

        # If DB stored file as bytes (BLOB)
        if isinstance(value, (bytes, bytearray)):
            data = bytes(value)
            mime = 'application/octet-stream'
            if data.startswith(b'%PDF'):
                mime = 'application/pdf'
            elif data.startswith(b'\xff\xd8'):
                mime = 'image/jpeg'
            elif data.startswith(b'\x89PNG'):
                mime = 'image/png'
            elif data.startswith(b'PK\x03\x04'):  # DOCX/XLSX - serve as octet-stream for Google Docs Viewer
                mime = 'application/octet-stream'
            # Force inline display and no caching so Google Docs can fetch it
            from flask import make_response
            response = make_response(data)
            response.headers['Content-Type'] = mime
            response.headers['Content-Disposition'] = 'inline'
            response.headers['Cache-Control'] = 'public, max-age=3600'
            return response

        # If DB stored a string (filename or URL path)
        if isinstance(value, str):
            import os
            if value.startswith('http://') or value.startswith('https://'):
                return redirect(value)

            local_path = os.path.join(app.root_path, UPLOAD_FOLDER, value)
            if os.path.exists(local_path):
                ext = os.path.splitext(value)[1].lower()
                mime = 'application/octet-stream'
                if ext == '.pdf':
                    mime = 'application/pdf'
                elif ext in ('.jpg', '.jpeg'):
                    mime = 'image/jpeg'
                elif ext == '.png':
                    mime = 'image/png'
                return send_from_directory(os.path.join(app.root_path, UPLOAD_FOLDER), value, as_attachment=False)

            base = app.config.get('UPLOAD_URL_BASE') or f"https://{app.config.get('MYSQL_HOST')}/uploads"
            external_url = base.rstrip('/') + '/' + value
            return redirect(external_url)

        return ("File format not supported", 415)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return (f"Error: {str(e)}", 500)

        return ("File format not supported", 415)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return (f"Error: {str(e)}", 500)


@app.route('/admin/job-description', methods=['GET', 'POST'])
@login_required
def admin_job_description():
    """Manage multiple job descriptions keyed by domain.
       Provides list view (GET) and actions (POST) to add/update/delete by id or domain.
    """
    conn = None
    cursor = None
    rows = []
    try:
        conn = get_db()
        cursor = conn.cursor()

        # Ensure the table exists with a sensible schema (best-effort)
        try:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS job_description (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    domain VARCHAR(255),
                    description TEXT
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
            conn.commit()
        except Exception:
            # ignore, we'll try to work with whatever schema exists
            print('Warning: could not ensure job_description schema')

        if request.method == 'POST':
            action = request.form.get('action')
            domain = (request.form.get('domain') or '').strip()
            desc = request.form.get('description', '').strip()
            row_id = request.form.get('id')
            try:
                if action == 'add':
                    if domain:
                        cursor.execute("INSERT INTO job_description (domain, description) VALUES (%s, %s)", (domain, desc))
                    else:
                        cursor.execute("INSERT INTO job_description (description) VALUES (%s)", (desc,))
                elif action in ('save', 'update'):
                    if row_id:
                        cursor.execute("UPDATE job_description SET domain=%s, description=%s WHERE id=%s", (domain or None, desc, int(row_id)))
                    elif domain:
                        cursor.execute("UPDATE job_description SET description=%s WHERE domain=%s", (desc, domain))
                elif action == 'delete':
                    if row_id:
                        cursor.execute("DELETE FROM job_description WHERE id=%s", (int(row_id),))
                    elif domain:
                        cursor.execute("DELETE FROM job_description WHERE domain=%s", (domain,))
                conn.commit()

                # Propagate job description change into approved_candidates.job_description
                try:
                    # Ensure approved_candidates has job_description column (best-effort)
                    try:
                        cursor.execute("ALTER TABLE approved_candidates ADD COLUMN IF NOT EXISTS job_description TEXT")
                    except Exception:
                        # some MySQL versions don't support IF NOT EXISTS for ALTER; try without IF NOT EXISTS
                        try:
                            cursor.execute("ALTER TABLE approved_candidates ADD COLUMN job_description TEXT")
                        except Exception:
                            pass

                    # Update candidate records for this domain
                    if action in ('add', 'save', 'update'):
                        if domain:
                            cursor.execute("UPDATE approved_candidates SET job_description=%s WHERE domain=%s", (desc, domain))
                        else:
                            # no domain provided: set for all rows
                            cursor.execute("UPDATE approved_candidates SET job_description=%s", (desc,))
                    elif action == 'delete':
                        if domain:
                            cursor.execute("UPDATE approved_candidates SET job_description = NULL WHERE domain=%s", (domain,))
                        else:
                            cursor.execute("UPDATE approved_candidates SET job_description = NULL")
                    conn.commit()
                except Exception as e:
                    print('Warning: could not propagate job_description to approved_candidates:', e)
            except Exception as e:
                print('DB write error in admin_job_description:', e)
            return redirect(url_for('admin_job_description'))

        # GET: fetch all rows
        try:
                # Introspect job_description table columns to support legacy schemas
                try:
                    cursor.execute("SELECT COLUMN_NAME FROM information_schema.columns WHERE table_schema=%s AND table_name=%s ORDER BY ORDINAL_POSITION", (app.config.get('MYSQL_DB'), 'job_description'))
                    jd_cols = [r['COLUMN_NAME'] for r in cursor.fetchall()]
                except Exception:
                    jd_cols = []

                rows = []
                if jd_cols and set(['id', 'domain', 'description']).issubset(set(jd_cols)):
                    cursor.execute("SELECT id, domain, description FROM job_description ORDER BY domain IS NULL, domain ASC, id ASC")
                    rows = cursor.fetchall()
                else:
                    # fallback: try to read as many columns as possible
                    try:
                        cursor.execute("SELECT * FROM job_description")
                        raw = cursor.fetchall()
                        # normalize rows to have id/domain/description keys
                        for i, r in enumerate(raw):
                            # r may be dict or tuple depending on cursor
                            if isinstance(r, dict):
                                # find description-like column
                                desc = None
                                domain = None
                                rid = r.get('id') or r.get('ID') or None
                                for c in ('description', 'job_description', 'jd', 'text', 'desc'):
                                    if c in r and r.get(c):
                                        desc = r.get(c)
                                        break
                                # attempt domain column
                                for c in ('domain', 'name'):
                                    if c in r and r.get(c):
                                        domain = r.get(c)
                                        break
                                rows.append({'id': rid or (i+1), 'domain': domain, 'description': desc})
                            else:
                                # tuple-like row; map first text column as description
                                rows.append({'id': i+1, 'domain': None, 'description': str(r)})
                    except Exception as e:
                        print('DB read error in admin_job_description (fallback):', e)
                        rows = []
        except Exception as e:
            print('DB read error in admin_job_description:', e)
            rows = []

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

    return render_template('admin_job_description.html', rows=rows)


# Check what table name is resolved
conn = get_db()
cur = conn.cursor()

table = get_resolved_table('free_internship')
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
        @app.before_first_request
        def ensure_approved_candidates_job_description_column():
            """Best-effort: ensure `approved_candidates.job_description` exists so SQLAlchemy queries don't fail.
               Runs once before the first request. Non-fatal on error.
            """
            conn = None
            cur = None
            try:
                conn = get_db()
                cur = conn.cursor()
                db_name = app.config.get('MYSQL_DB')
                cur.execute("SELECT COLUMN_NAME FROM information_schema.columns WHERE table_schema=%s AND table_name=%s", (db_name, 'approved_candidates'))
                cols = [r['COLUMN_NAME'] for r in cur.fetchall()]
                if 'job_description' not in cols:
                    try:
                        cur.execute("ALTER TABLE approved_candidates ADD COLUMN job_description TEXT")
                        conn.commit()
                        print('Added approved_candidates.job_description column')
                    except Exception as e:
                        # If ALTER fails, log and continue; the app will handle missing column gracefully later
                        print('Could not add approved_candidates.job_description column:', e)
            except Exception as e:
                print('Error during schema ensure step:', e)
            finally:
                try:
                    if cur:
                        cur.close()
                except Exception:
                    pass
                try:
                    if conn:
                        conn.close()
                except Exception:
                    pass
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
    # Disable the interactive debugger resources in production/dev-run by forcing debug=False
    # If you need debug features, set them explicitly via config and be aware
    # that the Werkzeug debugger will serve extra resources (seen as __debugger__ requests).
    app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)
