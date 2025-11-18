from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask import send_from_directory, send_file
import pymysql
import pymysql.cursors
import io
from functools import wraps
import json
import base64
import os
import re
from datetime import datetime

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
from admin_email_sender import mail, send_accept_email, send_reject_email, send_offer_letter_email, send_certificate_email
mail.init_app(app)

# Files uploaded path (change via env or config if needed)
UPLOAD_FOLDER = app.config.get('UPLOAD_FOLDER', 'uploads')
# Lightweight health endpoint so the server can be validated without DB access
@app.route('/ping')
def ping():
    return 'pong', 200
# Database connection helper with timeout and retry
def get_db():
    """Get database connection with timeout handling"""
    return pymysql.connect(
        host=app.config.get('MYSQL_HOST'),
        user=app.config.get('MYSQL_USER'),
        password=app.config.get('MYSQL_PASSWORD'),
        database=app.config.get('MYSQL_DB'),
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor,
        read_timeout=30,
        write_timeout=30,
        connect_timeout=10,
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
except Exception as e:
    print('Warning: Could not check/create approved_candidates.job_description column:', e)

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


# ===== CANDIDATE ID GENERATION FUNCTION =====
"""
Candidate ID Generation Logic:
Format: SIN + YY + XX + NNN
- SIN: Permanent prefix
- YY: Current year (last 2 digits)
- XX: Domain code (2 letters)
- NNN: Sequential counter for that domain in that year (001, 002, ...)

Domain Codes:
- FULL STACK DEVELOPER -> FD
- ARTIFICIAL INTELLIGENCE -> AI
- DATA SCIENCE -> DS
- DATA ANALYSIS -> DA
- MACHINE LEARNING -> ML
- ANDROID APP DEVELOPMENT -> AD
- SQL DEVELOPER -> SQ
- HUMAN RESOURCE -> HR
"""

DOMAIN_CODES = {
    # Preferred canonical mappings
    'full stack developer': 'FD',
    'fullstack developer': 'FD',
    'full-stack developer': 'FD',
    'full stack': 'FD',
    'fullstack': 'FD',
    'fd': 'FD',

    'artificial intelligence': 'AI',
    'ai': 'AI',

    'data science': 'DS',
    'datascience': 'DS',

    'data analysis': 'DA',
    'data-analysis': 'DA',

    'machine learning': 'ML',
    'machine-learning': 'ML',

    'android app development': 'AD',
    'android': 'AD',
    'mobile app development': 'AD',

    'sql developer': 'SQ',
    'sql': 'SQ',
    'database': 'SQ',

    'human resource': 'HR',
    'hr': 'HR',
}

def get_domain_code(domain_str):
    """Convert domain name to 2-letter code.

    This function attempts several strategies to avoid returning the fallback 'XX':
    1. Exact (normalized) match against `DOMAIN_CODES`.
    2. Token-based heuristics (checks for keywords present in the domain string).
    3. Short-circuit checks for common abbreviations.

    Returns 'XX' only if no reasonable mapping is found.
    """
    import re
    if not domain_str:
        return 'XX'

    domain_lower = domain_str.lower().strip()

    # Direct normalized lookup first
    if domain_lower in DOMAIN_CODES:
        return DOMAIN_CODES[domain_lower]

    # Tokenize words (alphanumeric tokens)
    tokens = re.findall(r"\w+", domain_lower)
    token_set = set(tokens)

    # Heuristic rules
    try:
        if 'full' in token_set and 'stack' in token_set:
            return 'FD'
        if 'fullstack' in token_set or 'full-stack' in domain_lower:
            return 'FD'

        if 'artificial' in token_set or 'ai' in token_set:
            return 'AI'

        if 'data' in token_set and 'science' in token_set:
            return 'DS'
        if 'data' in token_set and 'analysis' in token_set:
            return 'DA'

        if 'machine' in token_set and 'learning' in token_set:
            return 'ML'

        if 'android' in token_set or 'mobile' in token_set:
            return 'AD'

        if 'sql' in token_set or 'database' in token_set:
            return 'SQ'

        if ('human' in token_set and 'resource' in token_set) or 'hr' in token_set:
            return 'HR'

        # Last-ditch: if the domain string itself looks like a 2-letter code, accept it
        if re.fullmatch(r'[A-Za-z]{2}', domain_lower):
            return domain_lower.upper()
    except Exception:
        pass

    # Log unexpected domain strings so they can be added to the map later
    app.logger.warning(f"Unknown domain mapping for '{domain_str}' — using fallback 'XX'")
    return 'XX'

def generate_candidate_id(domain_str, conn=None):
    """
    Generate unique candidate ID based on domain and year.
    Format: SIN25FD001 (example for Full Stack Developer in 2025)
    
    Args:
        domain_str: Name of the domain/role
        conn: Database connection (optional; will create if not provided)
    
    Returns:
        Unique candidate ID string or None if error
    """
    try:
        should_close = False
        if conn is None:
            conn = get_db()
            should_close = True
        
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        # Get current year (last 2 digits)
        from datetime import datetime
        year_suffix = str(datetime.now().year)[-2:]  # e.g., '25' for 2025
        
        # Get domain code
        domain_code = get_domain_code(domain_str)
        
        # Build prefix to search for
        prefix = f"SIN{year_suffix}{domain_code}"  # e.g., "SIN25FD"
        
        # Get the highest counter for this prefix
        cursor.execute("""
            SELECT candidate_id FROM Selected 
            WHERE candidate_id LIKE %s 
            ORDER BY candidate_id DESC 
            LIMIT 1
        """, (f"{prefix}%",))
        
        last_row = cursor.fetchone()
        next_counter = 1
        
        if last_row:
            last_id = last_row.get('candidate_id', '')
            # Extract the counter part (last 3 digits)
            try:
                counter_str = last_id[-3:]
                last_counter = int(counter_str)
                next_counter = last_counter + 1
            except (ValueError, IndexError):
                next_counter = 1
        
        # Format with leading zeros (3 digits)
        candidate_id = f"{prefix}{next_counter:03d}"
        
        if should_close:
            cursor.close()
            conn.close()
        
        app.logger.info(f"Generated candidate_id: {candidate_id} for domain: {domain_str}")
        return candidate_id
        
    except Exception as e:
        app.logger.error(f"Error generating candidate_id: {e}")
        return None


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


@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    """Render admin dashboard"""
    return render_template('admin_dashboard.html')

@app.route('/admin/selected')
@login_required
def admin_selected():
    """Render selected candidates page"""
    return render_template('admin_selected.html')

@app.route('/admin/approved-candidates')
@login_required
def admin_approved_candidates():
    """Render approved candidates page"""
    return render_template('admin_approved_candidates.html')

@app.route('/admin/issue-certificate')
@login_required
def admin_issue_certificate():
    """Render the Issue Certificate page"""
    return render_template('admin_issue_certificate.html')

@app.route('/admin/logout')
def admin_logout():
    """Logout route"""
    session.clear()
    return redirect(url_for('admin_login'))


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
        # If free internships, enrich rows with resume score from resume_score table
        if internship_type == 'free' and rows:
            try:
                # Join resume_score by free_internship_application_id matching internship row id
                score_map = {}
                try:
                    cursor.execute("""
                        SELECT free_internship_application_id, score 
                        FROM resume_score
                    """)
                    for row in cursor.fetchall():
                        try:
                            app_id = row.get('free_internship_application_id') if isinstance(row, dict) else row[0]
                            score = row.get('score') if isinstance(row, dict) else row[1]
                            if app_id is not None:
                                score_map[str(app_id)] = score
                        except Exception:
                            continue
                except Exception as e:
                    print(f'Warning: Could not fetch resume_score data: {e}')
                    score_map = {}

                # Attach resume_score to each returned internship row by matching id
                for r in rows:
                    internship_id = r.get('id')
                    if internship_id is not None and str(internship_id) in score_map:
                        r['resume_score'] = score_map[str(internship_id)]
                    else:
                        r['resume_score'] = None
                
                # Sort rows by resume_score in descending order (highest score first)
                rows.sort(key=lambda x: (x.get('resume_score') is None, -x.get('resume_score') if x.get('resume_score') is not None else 0))
            except Exception as e:
                print(f'Warning: Could not enrich with resume_score: {e}')

        cursor.close()
        conn.close()
        return jsonify({'success': True, 'data': rows})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/admin/api/get-selected')
@login_required
def admin_api_get_selected():
    """Fetch all rows from Selected table where status = 'ongoing' using exact SQL query"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Execute exact query: SELECT * FROM `Selected` WHERE status = 'ongoing' ORDER BY approved_date DESC
        try:
            cursor.execute("SELECT * FROM `Selected` WHERE status = 'ongoing' ORDER BY approved_date DESC")
            rows = cursor.fetchall()
            print(f"✓ Fetched {len(rows)} rows from Selected table (status='ongoing')")
            
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


@app.route('/admin/api/get-completed-candidates')
@login_required
def admin_api_get_completed_candidates():
    """Fetch all rows from Selected table where status = 'completed' for certificate issuance"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Execute query: SELECT * FROM Selected WHERE status = 'completed'
        try:
            cursor.execute("SELECT * FROM `Selected` WHERE status = 'completed' ORDER BY completion_date DESC")
            rows = cursor.fetchall()
            app.logger.info(f"✓ Fetched {len(rows)} completed rows from Selected table")
            
            # Convert bytes to base64 strings for JSON serialization
            processed_rows = []
            for row in rows:
                if isinstance(row, dict):
                    processed_row = {}
                    for key, val in row.items():
                        if isinstance(val, bytes):
                            import base64
                            processed_row[key] = base64.b64encode(val).decode('utf-8')
                        else:
                            processed_row[key] = val
                    processed_rows.append(processed_row)
                else:
                    processed_rows.append(row)
            
            if processed_rows:
                app.logger.info(f"  Total processed rows: {len(processed_rows)}")
                
        except Exception as e:
            app.logger.error(f"✗ Query failed: {e}")
            processed_rows = []
        
        cursor.close()
        conn.close()
        
        return jsonify({'success': True, 'data': processed_rows})
    except Exception as e:
        app.logger.error(f"✗ Exception in /admin/api/get-completed-candidates: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/admin/api/send-report-form-email', methods=['POST'])
@login_required
def admin_api_send_report_form_email():
    """Send report form email to candidate and mark their Selected status as completed."""
    try:
        data = request.get_json()
        usn = data.get('usn', '').strip()
        email = data.get('email', '').strip()
        name = data.get('name', '').strip()

        if not usn or not email or not name:
            return jsonify({'success': False, 'error': 'Missing required fields: usn, email, name'}), 400

        # Update Selected table status to 'completed'
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('UPDATE `Selected` SET status = %s WHERE usn = %s', ('completed', usn))
        conn.commit()
        rows_affected = cursor.rowcount
        cursor.close()

        if rows_affected == 0:
            conn.close()
            return jsonify({'success': False, 'error': f'No candidate found with USN: {usn}'}), 404

        conn.close()

        # Send email with report form link
        try:
            from admin_email_sender import send_report_form_email
            send_report_form_email(email, name)
        except Exception as email_error:
            app.logger.warning(f"⚠ Email sending warning: {email_error}")
            # Don't fail the API call if email fails

        return jsonify({
            'success': True,
            'message': f'Email sent to {email} and status updated to completed',
            'data': {
                'usn': usn,
                'email': email,
                'name': name
            }
        })

    except Exception as e:
        app.logger.error(f"✗ Exception in /admin/api/send-report-form-email: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/admin/api/update-approved-candidate-domain', methods=['POST'])
@login_required
def admin_api_update_approved_candidate_domain():
    """Update domain of an approved candidate before accepting them."""
    try:
        data = request.get_json()
        candidate_id = data.get('candidate_id')
        new_domain = data.get('domain', '').strip()

        if not candidate_id or not new_domain:
            return jsonify({'success': False, 'error': 'Missing candidate_id or domain'}), 400

        # Find and update the approved candidate
        try:
            approved_candidate = ApprovedCandidate.query.filter_by(user_id=candidate_id).first()
            if not approved_candidate:
                # Try by application_id
                approved_candidate = ApprovedCandidate.query.filter_by(application_id=str(candidate_id)).first()
            
            if not approved_candidate:
                return jsonify({'success': False, 'error': f'Approved candidate not found with ID: {candidate_id}'}), 404

            # Update the domain
            approved_candidate.domain = new_domain
            db.session.commit()
            
            app.logger.info(f"✓ Updated domain for approved candidate {candidate_id} to {new_domain}")
            return jsonify({
                'success': True,
                'message': f'Domain updated to {new_domain}',
                'data': {
                    'candidate_id': candidate_id,
                    'new_domain': new_domain
                }
            })
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Failed to update approved candidate domain: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    except Exception as e:
        app.logger.error(f"✗ Exception in /admin/api/update-approved-candidate-domain: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/admin/api/get-selected-candidate/<identifier>')
@login_required
def admin_api_get_selected_candidate(identifier):
    """Fetch a single Selected record by application_id, user_id (numeric) or USN (string)."""
    try:
        conn = get_db()
        cursor = conn.cursor()

        # Try numeric match first
        row = None
        try:
            if identifier.isdigit():
                # Try application_id or user_id numeric match
                cursor.execute('SELECT * FROM `Selected` WHERE application_id = %s LIMIT 1', (int(identifier),))
                row = cursor.fetchone()
                if not row:
                    cursor.execute('SELECT * FROM `Selected` WHERE user_id = %s LIMIT 1', (int(identifier),))
                    row = cursor.fetchone()
        except Exception:
            row = None

        # If not found and identifier is non-numeric, try USN match
        if not row:
            try:
                cursor.execute('SELECT * FROM `Selected` WHERE usn = %s LIMIT 1', (identifier,))
                row = cursor.fetchone()
            except Exception:
                row = None

        cursor.close()
        conn.close()

        if not row:
            return jsonify({'success': False, 'error': 'Selected candidate not found'}), 404

        # Convert bytes to base64 for any binary fields
        processed = {}
        for k, v in (row.items() if isinstance(row, dict) else []):
            if isinstance(v, bytes):
                import base64
                processed[k] = base64.b64encode(v).decode('utf-8')
            else:
                processed[k] = v

        return jsonify({'success': True, 'data': processed})
    except Exception as e:
        print(f"✗ Exception in /admin/api/get-selected-candidate: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/admin/api/get-approved-candidates')
@login_required
def admin_api_get_approved_candidates():
    """Fetch all approved candidates - lightweight version without large BLOBs for list view"""
    max_retries = 3
    retry_count = 0

    import traceback

    # If the admin session is not present, return JSON 401 instead of redirecting (helps AJAX callers)
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401

    while retry_count < max_retries:
        try:
            # Query all approved candidates ordered by created_at descending
            # Use with_entities to exclude large BLOB columns for faster loading
            from sqlalchemy import func
            approved_candidates = ApprovedCandidate.query.order_by(ApprovedCandidate.created_at.desc()).all()

            # Convert to list of dictionaries - EXCLUDING large BLOBs for speed
            processed_rows = []
            for candidate in approved_candidates:
                candidate_dict = {
                    'usn': candidate.usn,
                    'application_id': candidate.application_id,
                    'user_id': candidate.user_id,
                    'name': candidate.name,
                    'email': candidate.email,
                    'phone_number': candidate.phone_number,
                    'year': candidate.year,
                    'qualification': candidate.qualification,
                    'branch': candidate.branch,
                    'college': candidate.college,
                    'domain': candidate.domain,
                    'mode_of_interview': candidate.mode_of_interview,
                    'resume_name': candidate.resume_name,
                    'project_document_name': candidate.project_document_name,
                    'id_proof_name': candidate.id_proof_name,
                    'job_description': candidate.job_description,
                }
                
                # Fetch slot_booking data for this candidate (if exists)
                slot_date = None
                slot_time = None
                try:
                    conn = get_db()
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT slot_date, slot_time FROM slot_booking WHERE applicant_id = %s LIMIT 1",
                        (candidate.user_id,)
                    )
                    slot_row = cursor.fetchone()
                    if slot_row:
                        if isinstance(slot_row, dict):
                            slot_date = slot_row.get('slot_date')
                            slot_time = slot_row.get('slot_time')
                        else:
                            slot_date = slot_row[0] if len(slot_row) > 0 else None
                            slot_time = slot_row[1] if len(slot_row) > 1 else None
                    cursor.close()
                    conn.close()
                except Exception as e:
                    app.logger.warning(f"Could not fetch slot_booking for candidate {candidate.usn}: {e}")
                
                candidate_dict['slot_date'] = slot_date
                candidate_dict['slot_time'] = slot_time
                
                # ONLY include BLOB content if it exists - convert to base64
                # This allows the frontend to check if files exist without loading huge data
                if candidate.resume_content:
                    candidate_dict['resume_content'] = base64.b64encode(candidate.resume_content).decode('utf-8')
                if candidate.project_document_content:
                    candidate_dict['project_document_content'] = base64.b64encode(candidate.project_document_content).decode('utf-8')
                if candidate.id_proof_content:
                    candidate_dict['id_proof_content'] = base64.b64encode(candidate.id_proof_content).decode('utf-8')

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


@app.route('/admin/api/get-approved-candidate/<int:user_id>', methods=['GET'])
@login_required
def admin_api_get_approved_candidate(user_id):
    """Return a single approved candidate record by user_id or application_id."""
    try:
        # Try by user_id first
        candidate = ApprovedCandidate.query.filter_by(user_id=user_id).first()
        # Fallback to application_id as string
        if not candidate:
            candidate = ApprovedCandidate.query.filter_by(application_id=str(user_id)).first()

        if not candidate:
            return jsonify({'success': False, 'error': 'Candidate not found'}), 404

        candidate_dict = candidate.to_dict()

        # Fetch slot_booking data for this candidate (if exists)
        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT slot_date, slot_time FROM slot_booking WHERE applicant_id = %s LIMIT 1",
                (candidate.user_id,)
            )
            slot_row = cursor.fetchone()
            if slot_row:
                if isinstance(slot_row, dict):
                    candidate_dict['slot_date'] = slot_row.get('slot_date')
                    candidate_dict['slot_time'] = slot_row.get('slot_time')
                else:
                    candidate_dict['slot_date'] = slot_row[0] if len(slot_row) > 0 else None
                    candidate_dict['slot_time'] = slot_row[1] if len(slot_row) > 1 else None
            cursor.close()
            conn.close()
        except Exception as e:
            app.logger.warning(f"Could not fetch slot_booking for candidate {user_id}: {e}")

        # Convert BLOBs to base64 strings for JSON
        if candidate_dict.get('resume_content') and isinstance(candidate_dict['resume_content'], bytes):
            candidate_dict['resume_content'] = base64.b64encode(candidate_dict['resume_content']).decode('utf-8')
        if candidate_dict.get('project_document_content') and isinstance(candidate_dict['project_document_content'], bytes):
            candidate_dict['project_document_content'] = base64.b64encode(candidate_dict['project_document_content']).decode('utf-8')
        if candidate_dict.get('id_proof_content') and isinstance(candidate_dict['id_proof_content'], bytes):
            candidate_dict['id_proof_content'] = base64.b64encode(candidate_dict['id_proof_content']).decode('utf-8')

        return jsonify({'success': True, 'data': candidate_dict})
    except Exception as e:
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

def handle_approved_candidate_accept(approved_candidate, internship_type='free'):
    """Handle acceptance of an approved candidate - transfer to Selected table and generate offer letter"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Extract candidate details
        usn_val = approved_candidate.usn
        name_val = approved_candidate.name
        email_val = approved_candidate.email
        phone_val = approved_candidate.phone_number or ''
        year_val = approved_candidate.year or ''
        qualification_val = approved_candidate.qualification or ''
        branch_val = approved_candidate.branch or ''
        college_val = approved_candidate.college or ''
        domain_val = approved_candidate.domain or ''
        mode_of_interview_val = approved_candidate.mode_of_interview or 'online'
        
        # Create role: "domain name Intern"
        role_val = f"{domain_val} Intern" if domain_val else "Intern"
        
        # Check if already in Selected (avoid duplicates)
        cursor.execute("SELECT usn FROM Selected WHERE usn = %s LIMIT 1", (usn_val,))
        exists = cursor.fetchone()
        
        # Generate candidate_id
        candidate_id = generate_candidate_id(domain_val, conn)
        
        # Determine duration based on internship type
        duration_months = 1
        if internship_type in ('paid', 'remote-based opportunity', 'hybrid-based opportunity', 'on-site based opportunity'):
            duration_months = 3  # Default 3 months for paid/specified types
        
        if exists:
            # Update existing record
            try:
                update_sql = """UPDATE Selected SET
                    name = %s,
                    email = %s,
                    phone = %s,
                    year = %s,
                    qualification = %s,
                    branch = %s,
                    college = %s,
                    domain = %s,
                    roles = %s,
                    approved_date = CURDATE(),
                    status = 'ongoing',
                    completion_date = DATE_ADD(CURDATE(), INTERVAL %s MONTH),
                    candidate_id = %s,
                    mode_of_internship = %s
                    WHERE usn = %s"""
                
                cursor.execute(update_sql, (
                    name_val, email_val, phone_val,
                    year_val, qualification_val, branch_val, college_val, domain_val,
                    role_val, duration_months, candidate_id, internship_type, usn_val
                ))
                conn.commit()
                app.logger.info(f"Updated Selected record for approved candidate {usn_val}")
            except Exception as e:
                app.logger.error(f"Failed to update approved candidate in Selected: {e}")
                conn.rollback()
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'error': f'Failed to update Selected table: {e}'}), 500
        else:
            # Insert new record
            try:
                insert_sql = """INSERT INTO Selected 
                (name, email, phone, usn, year, qualification, branch, college, domain, roles,
                 approved_date, status, completion_date, candidate_id, mode_of_internship)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURDATE(), 'ongoing', DATE_ADD(CURDATE(), INTERVAL %s MONTH), %s, %s)"""
                
                cursor.execute(insert_sql, (
                    name_val, email_val, phone_val, usn_val, year_val,
                    qualification_val, branch_val, college_val, domain_val,
                    role_val, duration_months, candidate_id, internship_type
                ))
                conn.commit()
                app.logger.info(f"Inserted approved candidate {usn_val} into Selected with ID {candidate_id}")
            except Exception as e:
                app.logger.error(f"Failed to insert approved candidate into Selected: {e}")
                conn.rollback()
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'error': f'Failed to insert into Selected table: {e}'}), 500
        
        # Delete from approved_candidates table
        try:
            db.session.delete(approved_candidate)
            db.session.commit()
            app.logger.info(f"Deleted approved candidate {usn_val} from approved_candidates table")
        except Exception as e:
            app.logger.error(f"Failed to delete approved candidate from approved_candidates: {e}")
            db.session.rollback()
        
        cursor.close()
        conn.close()
        
        # Try to generate offer letter automatically
        offer_letter_ref = None
        offer_letter_filename = None
        try:
            import requests
            offer_letter_data = {
                'name': name_val,
                'usn': usn_val,
                'email': email_val,
                'college': college_val,
                'role': role_val,
                'duration': '3 months',  # Default duration
                'internship_type': internship_type
            }
            
            # Try to call the offer-letter-generator app API
            try:
                response = requests.post(
                    'http://localhost:5001/api/generate-offer',
                    json=offer_letter_data,
                    timeout=30
                )
                if response.status_code == 200:
                    result = response.json()
                    if result.get('success'):
                        offer_letter_ref = result.get('reference_number')
                        offer_letter_filename = result.get('filename')
                        app.logger.info(f"✓ Offer letter generated successfully for {usn_val} - Ref: {offer_letter_ref}")
                    else:
                        app.logger.warning(f"Offer letter generation error: {result.get('error', 'Unknown error')}")
                else:
                    app.logger.warning(f"Offer letter generation returned status {response.status_code}")
            except requests.exceptions.ConnectionError:
                app.logger.warning(f"Could not connect to offer-letter-generator service on localhost:5001 - ensure it's running")
            except Exception as e:
                app.logger.warning(f"Error generating offer letter: {e}")
        except Exception as e:
            app.logger.warning(f"Skipping offer letter generation: {e}")
        
        # Send acceptance email
        ok = send_accept_email(email_val, name_val or '', internship_type='free')
        
        response_data = {
            'success': True,
            'message': 'Accepted! Candidate moved to Selected',
            'candidate_id': candidate_id
        }
        
        if offer_letter_ref:
            response_data['offer_letter'] = {
                'reference': offer_letter_ref,
                'filename': offer_letter_filename
            }
        
        if ok:
            response_data['message'] = 'Accepted! Offer letter generated and email sent'
        
        return jsonify(response_data)
    
    except Exception as e:
        app.logger.exception(f"Error handling approved candidate acceptance: {e}")
        return jsonify({'success': False, 'error': f'Error: {str(e)}'}), 500

@app.route('/accept/<int:user_id>', methods=['POST'])
@login_required
def admin_accept(user_id):
    """Accept an internship application and move to appropriate table"""
    
    # Extract internship type from request
    internship_type = 'free'
    try:
        if request.is_json:
            internship_type = request.get_json().get('internship_type', 'free')
        elif request.form:
            internship_type = request.form.get('internship_type', 'free')
    except Exception as e:
        app.logger.warning(f"Could not extract internship_type: {e}")
    
    # First check if this is an approved candidate (try by user_id or application_id)
    try:
        approved_candidate = ApprovedCandidate.query.filter_by(user_id=user_id).first()
        if not approved_candidate:
            # Try by application_id
            approved_candidate = ApprovedCandidate.query.filter_by(application_id=str(user_id)).first()
        
        if approved_candidate:
            # Handle approved candidate acceptance - move to Selected
            return handle_approved_candidate_accept(approved_candidate, internship_type)
    except Exception as e:
        app.logger.warning(f"Could not check approved candidates for user {user_id}: {e}")
    
    # Otherwise, handle as paid/free internship
    internship_type = request.args.get('type', 'free')
    email, name = _fetch_applicant_contact(user_id, internship_type)
    
    if not email:
        return jsonify({'success': False, 'error': 'Applicant email not found'}), 404

    details_for_email = {
        'application_id': user_id,
        'name': name or '',
        'email': email or ''
    }

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
    except Exception as e:
        app.logger.warning(f"Could not update status: {e}")

    # ===== FREE INTERNSHIP: Move to approved_candidates =====
    if internship_type == 'free':
        try:
            conn = get_db()
            cursor = conn.cursor()
            free_table = get_resolved_table('free_internship')
            
            # Fetch applicant row
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

            if not row:
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'error': 'Applicant not found'}), 404
            
            # Extract USN early to check for duplicates
            row_map = {k.lower(): v for k, v in (row.items() if isinstance(row, dict) else [])}
            usn_val = row_map.get('usn') or row_map.get('roll') or row_map.get('rollno') or f"APP{user_id}"
            
            # CHECK IF USN ALREADY EXISTS IN APPROVED_CANDIDATES
            try:
                existing_candidate = ApprovedCandidate.query.filter_by(usn=usn_val).first()
                if existing_candidate:
                    cursor.close()
                    conn.close()
                    app.logger.warning(f"Duplicate USN in approved_candidates: {usn_val}")
                    return jsonify({
                        'success': False, 
                        'error': f'This person is already present in the approved candidates list. USN: {usn_val} | Name: {existing_candidate.name}',
                        'code': 'DUPLICATE_USN'
                    }), 409
            except Exception as e:
                app.logger.warning(f"Could not check for duplicate USN: {e}")
            
            # Fetch BLOBs from free_document_store
            resume_blob = None
            project_blob = None
            id_proof_blob = None
            resume_name = None
            project_document_name = None
            id_proof_name = None
            
            resume_name = row_map.get('resume')
            project_document_name = row_map.get('project_document')
            id_proof_name = row_map.get('id_proof')
            
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
                        resume_blob = blob_row[0] if len(blob_row) > 0 else None
                        project_blob = blob_row[1] if len(blob_row) > 1 else None
                        id_proof_blob = blob_row[2] if len(blob_row) > 2 else None
            except Exception as e:
                app.logger.warning(f"Could not fetch document BLOBs: {e}")
            
            cursor.close()
            conn.close()
            
            # Extract applicant details
            name_val = row_map.get('name') or row_map.get('full_name') or ''
            email_val = row_map.get('email') or row_map.get('applicant_email') or ''
            phone_val = row_map.get('phone') or row_map.get('mobile') or ''
            year_val = row_map.get('year') or row_map.get('sem') or ''
            qualification_val = row_map.get('qualification') or ''
            branch_val = row_map.get('branch') or row_map.get('department') or ''
            college_val = row_map.get('college') or ''
            domain_val = row_map.get('domain') or ''
            mode_of_interview_val = row_map.get('mode_of_interview') or 'online'
            
            # Extract or create application_id from free_internship table
            # Use existing application_id if available, otherwise use user_id (which is the 'id' from free_internship table)
            application_id_val = row_map.get('application_id') or str(user_id)
            
            # Create and insert ApprovedCandidate record
            try:
                approved_candidate = ApprovedCandidate(
                    usn=usn_val,
                    application_id=application_id_val,
                    user_id=user_id,  # This is the 'id' from free_internship table
                    name=name_val,
                    email=email_val,
                    phone_number=phone_val,
                    year=year_val,
                    qualification=qualification_val,
                    branch=branch_val,
                    college=college_val,
                    domain=domain_val,
                    mode_of_interview=mode_of_interview_val,
                    resume_name=resume_name,
                    resume_content=resume_blob,
                    project_document_name=project_document_name,
                    project_document_content=project_blob,
                    id_proof_name=id_proof_name,
                    id_proof_content=id_proof_blob
                )
                
                db.session.add(approved_candidate)
                db.session.commit()
                app.logger.info(f"✓ Successfully inserted free applicant {user_id} ({usn_val}) into approved_candidates")
                
                # Delete from free_internship_application and free_document_store
                try:
                    conn = get_db()
                    cursor = conn.cursor()
                    
                    cursor.execute("DELETE FROM free_document_store WHERE free_internship_application_id = %s", (user_id,))
                    conn.commit()
                    app.logger.info(f"✓ Deleted documents for free applicant {user_id}")
                    
                    cursor.execute(f"DELETE FROM {free_table} WHERE id = %s", (user_id,))
                    conn.commit()
                    app.logger.info(f"✓ Deleted free application for {user_id}")
                    
                    cursor.close()
                    conn.close()
                except Exception as e:
                    app.logger.warning(f"Error cleaning up free application: {e}")
                    try:
                        alt_table = free_table.replace('_application', '') if free_table.endswith('_application') else free_table + '_application'
                        conn = get_db()
                        cursor = conn.cursor()
                        cursor.execute(f"DELETE FROM {alt_table} WHERE id = %s", (user_id,))
                        conn.commit()
                        cursor.close()
                        conn.close()
                    except Exception as e2:
                        app.logger.warning(f"Could not delete from {alt_table}: {e2}")
                
            except Exception as e:
                app.logger.error(f"Failed to insert free applicant into approved_candidates: {e}")
                try:
                    db.session.rollback()
                except Exception:
                    pass
                return jsonify({'success': False, 'error': f'Failed to move to approved_candidates: {e}'}), 500
        
        except Exception as e:
            app.logger.exception(f"Error processing free internship: {e}")
            return jsonify({'success': False, 'error': f'Error: {str(e)}'}), 500
    
    # ===== PAID INTERNSHIP: Move to Selected =====
    elif internship_type == 'paid':
        try:
            conn = get_db()
            cursor = conn.cursor()
            paid_table = get_resolved_table('paid_internship')
            
            # Fetch applicant row
            row = None
            try:
                cursor.execute(f"SELECT * FROM {paid_table} WHERE id = %s LIMIT 1", (user_id,))
                row = cursor.fetchone()
            except Exception:
                alt_table = paid_table.replace('_application', '') if paid_table.endswith('_application') else paid_table + '_application'
                try:
                    cursor.execute(f"SELECT * FROM {alt_table} WHERE id = %s LIMIT 1", (user_id,))
                    row = cursor.fetchone()
                except Exception:
                    row = None

            if not row:
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'error': 'Applicant not found'}), 404
            
            # Extract basic info
            row_map = {k.lower(): v for k, v in (row.items() if isinstance(row, dict) else [])}
            
            # Extract USN early to check for duplicates in Selected table
            usn_val = row_map.get('usn') or row_map.get('roll') or row_map.get('rollno') or f"APP{user_id}"
            
            # CHECK IF USN ALREADY EXISTS IN SELECTED TABLE
            try:
                cursor.execute("SELECT id, name FROM Selected WHERE usn = %s LIMIT 1", (usn_val,))
                existing_in_selected = cursor.fetchone()
                if existing_in_selected:
                    cursor.close()
                    conn.close()
                    existing_name = existing_in_selected[1] if isinstance(existing_in_selected, tuple) else existing_in_selected.get('name', 'Unknown')
                    app.logger.warning(f"Duplicate USN in Selected: {usn_val}")
                    return jsonify({
                        'success': False, 
                        'error': f'This person is already present in the selected candidates list. USN: {usn_val} | Name: {existing_name}',
                        'code': 'DUPLICATE_USN'
                    }), 409
            except Exception as e:
                app.logger.warning(f"Error checking for duplicate USN in Selected: {e}")
            
            application_id = user_id
            name_val = row_map.get('name') or row_map.get('full_name') or ''
            email_val = row_map.get('email') or row_map.get('applicant_email') or ''
            phone_val = row_map.get('phone') or row_map.get('mobile') or row_map.get('contact_number') or ''
            year_val = row_map.get('year') or row_map.get('sem') or ''
            qualification_val = row_map.get('qualification') or ''
            branch_val = row_map.get('branch') or row_map.get('department') or ''
            college_val = row_map.get('college') or ''
            domain_val = row_map.get('domain') or ''
            project_description_val = row_map.get('project_description') or ''
            project_name_val = row_map.get('project_document') or row_map.get('project_name') or ''
            project_title_val = row_map.get('project_title') or project_name_val or ''
            internship_duration = row_map.get('internship_duration') or '1'  # Default 1 month if not specified
            
            # Convert duration to integer (in months)
            try:
                duration_months = int(internship_duration)
            except (ValueError, TypeError):
                duration_months = 1
            
            # Generate unique candidate_id for paid internship based on domain
            # Format: SIN25FD001 (SIN + year + domain_code + counter)
            candidate_id_val = generate_candidate_id(domain_val, conn)
            if not candidate_id_val:
                cursor.close()
                conn.close()
                app.logger.error(f"Failed to generate candidate_id for paid applicant {user_id}")
                return jsonify({'success': False, 'error': 'Failed to generate candidate ID'}), 500
            
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
            except Exception as e:
                app.logger.warning(f"Could not fetch project BLOB: {e}")
            
            # Insert into Selected table (with generated candidate_id, approved_date set to today, completion_date calculated)
            try:
                # Create role: "domain name Intern"
                role_val = f"{domain_val} Intern" if domain_val else "Intern"
                
                insert_sql = """INSERT INTO Selected 
                (candidate_id, name, email, phone, usn, year, qualification, branch, college, domain, roles,
                 project_description, internship_project_name, internship_project_content, project_title,
                 approved_date, status, completion_date, resend_count, mode_of_internship)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURDATE(), %s, DATE_ADD(CURDATE(), INTERVAL %s MONTH), %s, %s)"""
                
                cursor.execute(insert_sql, (
                    candidate_id_val, name_val, email_val, phone_val, usn_val, year_val,
                    qualification_val, branch_val, college_val, domain_val,
                    role_val, project_description_val, project_name_val, project_blob, project_title_val,
                    'ongoing', duration_months, 0, 'paid'
                ))
                conn.commit()
                app.logger.info(f"✓ Successfully inserted paid applicant {user_id} ({usn_val}) into Selected with candidate_id: {candidate_id_val} | Duration: {duration_months} months")
                
                # Auto-generate and store offer letter for paid internship
                try:
                    # Prepare offer letter data
                    internship_type = 'paid'
                    duration_str = f"{duration_months} month{'s' if duration_months != 1 else ''}"
                    
                    print(f"[DEBUG] Generating offer letter for {name_val} ({usn_val})")
                    print(f"[DEBUG] Params: college={college_val}, email={email_val}, role={role_val}, duration={duration_str}, type={internship_type}")
                    
                    # Generate offer letter PDF
                    offer_output, offer_ref_no = generate_offer_pdf(
                        name_val, 
                        usn_val, 
                        college_val, 
                        email_val, 
                        role_val, 
                        duration_str, 
                        internship_type
                    )
                    
                    print(f"[DEBUG] Offer generation result: output={offer_output}, ref_no={offer_ref_no}")
                    
                    if offer_output and offer_ref_no:
                        # Get PDF bytes
                        pdf_bytes = offer_output.getvalue()
                        
                        print(f"[DEBUG] PDF bytes obtained: type={type(pdf_bytes)}, size={len(pdf_bytes)}")
                        
                        # Store offer letter in database
                        update_sql = """UPDATE Selected SET 
                            offer_letter_pdf = %s,
                            offer_letter_reference = %s,
                            offer_letter_generated_date = NOW()
                            WHERE usn = %s"""
                        
                        cursor.execute(update_sql, (pdf_bytes, offer_ref_no, usn_val))
                        conn.commit()
                        app.logger.info(f"✓ Auto-generated and stored offer letter for paid internship {usn_val} with ref {offer_ref_no}")
                        print(f"✓ Offer letter stored in database for {usn_val}")
                        
                        # Send offer letter via email
                        try:
                            print(f"[DEBUG] Attempting to send offer letter to {email_val}")
                            print(f"[DEBUG] PDF bytes type: {type(pdf_bytes)}, size: {len(pdf_bytes) if pdf_bytes else 0}")
                            result = send_offer_letter_email(email_val, name_val, pdf_bytes, offer_ref_no)
                            if result:
                                app.logger.info(f"✓ Offer letter email sent to {email_val}")
                                print(f"✓ Offer letter email sent to {email_val}")
                            else:
                                app.logger.warning(f"Failed to send offer letter email to {email_val} - send function returned False")
                                print(f"❌ Offer letter email send failed for {email_val}")
                        except Exception as email_err:
                            app.logger.exception(f"Error sending offer letter email to {email_val}: {email_err}")
                            print(f"❌ Exception sending offer letter email: {email_err}")
                            import traceback
                            traceback.print_exc()
                    else:
                        app.logger.warning(f"Failed to auto-generate offer letter for paid internship {usn_val}")
                        print(f"❌ Offer letter generation failed for {usn_val}")
                except Exception as e:
                    app.logger.warning(f"Error auto-generating offer letter for paid internship {usn_val}: {e}")
                    print(f"❌ Exception during offer letter process: {e}")
                    import traceback
                    traceback.print_exc()
                
                # Delete from paid_internship_application and paid_document_store
                try:
                    cursor.execute("DELETE FROM paid_document_store WHERE paid_internship_application_id = %s", (user_id,))
                    conn.commit()
                    app.logger.info(f"✓ Deleted documents for paid applicant {user_id}")
                except Exception as e:
                    app.logger.warning(f"Could not delete documents: {e}")
                
                try:
                    cursor.execute(f"DELETE FROM {paid_table} WHERE id = %s", (user_id,))
                    conn.commit()
                    app.logger.info(f"✓ Deleted paid application for {user_id}")
                except Exception:
                    alt_table = paid_table.replace('_application', '') if paid_table.endswith('_application') else paid_table + '_application'
                    try:
                        cursor.execute(f"DELETE FROM {alt_table} WHERE id = %s", (user_id,))
                        conn.commit()
                        app.logger.info(f"✓ Deleted paid application from {alt_table}")
                    except Exception as e:
                        app.logger.warning(f"Could not delete: {e}")
                
            except Exception as e:
                app.logger.error(f"Error inserting paid applicant into Selected: {e}")
                conn.rollback()
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'error': f'Failed to move to Selected: {e}'}), 500
            
            cursor.close()
            conn.close()
        
        except Exception as e:
            app.logger.exception(f"Error processing paid internship: {e}")
            return jsonify({'success': False, 'error': f'Error: {str(e)}'}), 500

    # Send acceptance email
    interview_link = None
    if internship_type == 'free':
        interview_link = 'http://127.0.0.1:5000/interview-scheduler'
    
    ok = send_accept_email(email, name or '', details=details_for_email, interview_link=interview_link, internship_type=internship_type)
    
    resp = {'success': bool(ok)}
    if internship_type == 'free':
        resp['message'] = 'Application moved to approved_candidates and accept email sent'
    else:
        resp['message'] = 'Application moved to selected candidates and accept email sent'
    
    if not ok:
        resp['error'] = 'Failed to send email'
    
    return jsonify(resp), (200 if ok else 500)

def handle_approved_candidate_reject(approved_candidate):
    """Handle rejection of an approved candidate - delete from approved_candidates table"""
    try:
        email_val = approved_candidate.email
        name_val = approved_candidate.name
        usn_val = approved_candidate.usn
        user_id_val = approved_candidate.user_id
        reason = request.get_json().get('reason', 'Not specified') if request.is_json else 'Not specified'
        
        # First, delete any related records in slot_booking table (due to foreign key constraint)
        try:
            conn = get_db()
            cursor = conn.cursor()
            
            # Delete from slot_booking where applicant_id matches this candidate's user_id
            cursor.execute("DELETE FROM slot_booking WHERE applicant_id = %s", (user_id_val,))
            conn.commit()
            app.logger.info(f"Deleted slot_booking records for approved candidate {usn_val}")
            
            cursor.close()
            conn.close()
        except Exception as e:
            app.logger.warning(f"Warning: Could not delete slot_booking records: {e}")
            # Continue anyway - we'll try to delete the candidate
        
        # Delete from approved_candidates table
        try:
            db.session.delete(approved_candidate)
            db.session.commit()
            app.logger.info(f"Deleted rejected approved candidate {usn_val} from approved_candidates table")
        except Exception as e:
            app.logger.error(f"Failed to delete approved candidate from approved_candidates: {e}")
            db.session.rollback()
            return jsonify({'success': False, 'error': f'Failed to delete candidate: {e}'}), 500
        
        # Send rejection email
        ok = send_reject_email(email_val, name_val or '', reason, internship_type='free')
        
        if ok:
            return jsonify({'success': True, 'message': 'Candidate rejected and all data deleted. Rejection email sent'})
        else:
            return jsonify({'success': True, 'message': 'Candidate rejected and all data deleted, but email failed to send'})
    
    except Exception as e:
        app.logger.exception(f"Error handling approved candidate rejection: {e}")
        return jsonify({'success': False, 'error': f'Error: {str(e)}'}), 500

@app.route('/reject/<int:user_id>', methods=['POST'])
@login_required
def admin_reject(user_id):
    """Reject an internship application: delete all candidate data and documents completely."""
    # First check if this is an approved candidate
    try:
        approved_candidate = ApprovedCandidate.query.filter_by(user_id=user_id).first()
        if not approved_candidate:
            # Try by application_id
            approved_candidate = ApprovedCandidate.query.filter_by(application_id=str(user_id)).first()
        
        if approved_candidate:
            # Handle approved candidate rejection
            return handle_approved_candidate_reject(approved_candidate)
    except Exception as e:
        app.logger.warning(f"Could not check approved candidates for user {user_id}: {e}")
    
    # Otherwise, handle as paid/free internship
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
                        elif data.startswith(b'PK\x03\x04'):  # DOCX/XLSX magic bytes
                            if b'word' in data[:1000]:
                                detected_ext = 'docx'
                            else:
                                detected_ext = 'xlsx'
                        
                        cursor.close()
                        conn.close()
                        return send_file(io.BytesIO(data), mimetype='application/octet-stream', as_attachment=False, download_name=f"{file_type}.{detected_ext}")
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
                        
                        if data.startswith(b'%PDF'):
                            detected_ext = 'pdf'
                        elif data.startswith(b'\xff\xd8'):
                            detected_ext = 'jpg'
                        elif data.startswith(b'\x89PNG'):
                            detected_ext = 'png'
                        elif data.startswith(b'PK\x03\x04'):  # DOCX/XLSX magic bytes
                            if b'word' in data[:1000]:
                                detected_ext = 'docx'
                            else:
                                detected_ext = 'xlsx'
                        
                        cursor.close()
                        conn.close()
                        return send_file(io.BytesIO(data), mimetype='application/octet-stream', as_attachment=True, download_name=f"{file_type}.{detected_ext}")
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


# ==================== CERTIFICATE GENERATION (Using SWIZ_CERTI) ====================

from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas

# Certificate configuration pointing to SWIZ_CERTI folder
CERT_BASE_PATH = os.path.join(os.path.dirname(__file__), 'SWIZ CERTI', 'certificate-generator')
CERTIFICATE_TEMPLATE_PATH = os.path.join(CERT_BASE_PATH, 'certificate', 'certificate_template.pdf')
GENERATED_CERTS_PATH = os.path.join(CERT_BASE_PATH, 'generated')
SERIAL_FILE = os.path.join(CERT_BASE_PATH, 'serial.json')

def get_monthwise_serial(month):
    """Get month-wise serial number for certificate (from SWIZ_CERTI)"""
    # Ensure serial.json directory exists
    os.makedirs(CERT_BASE_PATH, exist_ok=True)
    
    # If serial.json doesn't exist, create it
    if not os.path.exists(SERIAL_FILE):
        data = {"month": month, "serial": 0}
        with open(SERIAL_FILE, "w") as f:
            json.dump(data, f)
    
    # Load file data
    with open(SERIAL_FILE, "r") as f:
        data = json.load(f)
    
    # Reset if new month
    if data.get("month") != month:
        data["month"] = month
        data["serial"] = 1
    else:
        data["serial"] = data.get("serial", 0) + 1
    
    # Save back to file
    with open(SERIAL_FILE, "w") as f:
        json.dump(data, f)
    
    # Return formatted like 001, 002, 003
    return f"{data['serial']:03}"


def generate_certificate_pdf(candidate_name):
    """Generate a certificate PDF using SWIZ_CERTI certificate template"""
    
    # Ensure output directory exists
    os.makedirs(GENERATED_CERTS_PATH, exist_ok=True)
    
    # Check if template exists
    if not os.path.exists(CERTIFICATE_TEMPLATE_PATH):
        raise FileNotFoundError(f"Certificate template not found at: {CERTIFICATE_TEMPLATE_PATH}")
    
    # Date & Serial Logic
    now = datetime.now()
    year = now.year
    month = now.strftime("%b").upper()  # JAN, FEB, MAR...
    serial_no = get_monthwise_serial(month)
    
    # Certificate ID (display format)
    certificate_id = f"SZS_CERT_{year}_{month}_{serial_no}"
    
    # File-safe name for saving
    file_name = certificate_id.replace("/", "_") + ".pdf"
    output_file = os.path.join(GENERATED_CERTS_PATH, file_name)
    
    try:
        # PDF Generation (using SWIZ_CERTI logic)
        # Open template PDF with proper file handling
        with open(CERTIFICATE_TEMPLATE_PATH, "rb") as template_file:
            existing_pdf = PdfReader(template_file)
            page = existing_pdf.pages[0]
            
            media = page.mediabox
            width = float(media.width)
            height = float(media.height)
            
            # Create text overlay with ReportLab
            packet = io.BytesIO()
            can = canvas.Canvas(packet, pagesize=(width, height))
            
            # Set Font and draw candidate name
            can.setFont("Times-Italic", 33)
            
            # Center name
            text_width = can.stringWidth(candidate_name, "Times-Italic", 33)
            x_position = (width - text_width) / 2
            y_position = height * 0.46  # Center vertically
            
            can.drawString(x_position, y_position, candidate_name)
            can.save()
            
            # Merge text overlay with template
            packet.seek(0)
            name_pdf = PdfReader(packet)
            
            writer = PdfWriter()
            page.merge_page(name_pdf.pages[0])
            writer.add_page(page)
            
            # Write to file in SWIZ_CERTI folder
            with open(output_file, "wb") as f:
                writer.write(f)
    
    except Exception as e:
        raise Exception(f"PDF generation error: {str(e)}")
    
    # Also copy the generated certificate back to the main project folder
    try:
        project_generated_dir = os.path.join(os.path.dirname(__file__), 'generated_certificates')
        os.makedirs(project_generated_dir, exist_ok=True)
        copied_path = os.path.join(project_generated_dir, os.path.basename(output_file))
        # Use shutil to preserve file
        import shutil
        shutil.copy2(output_file, copied_path)
    except Exception as e:
        # Log but don't fail: original file in SWIZ_CERTI exists
        app.logger.warning(f"Failed to copy generated certificate to project folder: {e}")
        copied_path = None

    # Return file path in SWIZ_CERTI, certificate ID and optional copied path
    return output_file, certificate_id, copied_path


@app.route('/admin/api/generate-certificate/<candidate_id>', methods=['POST'])
@login_required
def generate_certificate(candidate_id):
    """Generate certificate for a candidate using SWIZ_CERTI and store in database.

    Accepts numeric or string identifiers. Tries multiple candidate fields
    to locate the Selected record to store certificate.
    """
    try:
        # Lookup candidate in Selected table (primary source for certificate details)
        conn = get_db()
        cursor = conn.cursor()
        row = None
        usn_for_storage = None
        
        try:
            # If numeric, try application_id or user_id
            if str(candidate_id).isdigit():
                cursor.execute('SELECT * FROM `Selected` WHERE application_id = %s LIMIT 1', (int(candidate_id),))
                row = cursor.fetchone()
                if not row:
                    cursor.execute('SELECT * FROM `Selected` WHERE user_id = %s LIMIT 1', (int(candidate_id),))
                    row = cursor.fetchone()

            # If not found, try candidate_id column and USN
            if not row:
                try:
                    cursor.execute('SELECT * FROM `Selected` WHERE candidate_id = %s LIMIT 1', (candidate_id,))
                    row = cursor.fetchone()
                except Exception:
                    row = row
            if not row:
                try:
                    cursor.execute('SELECT * FROM `Selected` WHERE usn = %s LIMIT 1', (candidate_id,))
                    row = cursor.fetchone()
                except Exception:
                    row = row
        finally:
            try:
                cursor.close()
            except Exception:
                pass
            try:
                conn.close()
            except Exception:
                pass

        if not row:
            app.logger.warning(f"Selected lookup failed for identifier: {candidate_id}")
            return jsonify({'success': False, 'error': 'Candidate not found in Selected table'}), 404

        # Extract name from Selected row and get USN for database storage
        candidate_name = (row.get('name') or '').strip().upper()
        usn_for_storage = row.get('usn', '')
        candidate_id_val = row.get('candidate_id', '')
        candidate_email = row.get('email', '')
        
        if not candidate_name:
            return jsonify({'success': False, 'error': 'Candidate name not found'}), 400

        app.logger.info(f"Certificate lookup - candidate_id: {candidate_id}, usn_for_storage: {usn_for_storage}, candidate_id_val: {candidate_id_val}")

        # Generate certificate using SWIZ_CERTI logic
        cert_file_path, certificate_id, copied_path = generate_certificate_pdf(candidate_name)
        app.logger.info(f"Generated certificate {certificate_id} at {cert_file_path}; copied to {copied_path}")

        # Read the generated PDF as bytes
        with open(cert_file_path, 'rb') as f:
            pdf_bytes = f.read()
        
        # Store certificate in database
        try:
            conn = get_db()
            cursor = conn.cursor()
            
            # Use USN for storage, fall back to candidate_id if USN is empty
            lookup_value = usn_for_storage if usn_for_storage else candidate_id_val
            lookup_column = 'usn' if usn_for_storage else 'candidate_id'
            
            if not lookup_value:
                app.logger.warning(f"Both USN and candidate_id are empty for certificate storage")
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'error': 'Cannot store certificate - no valid identifier'}), 500
            
            update_sql = f"""UPDATE Selected SET 
                certificate_pdf = %s,
                certificate_id = %s,
                certificate_generated_date = NOW()
                WHERE {lookup_column} = %s"""
            
            cursor.execute(update_sql, (pdf_bytes, certificate_id, lookup_value))
            conn.commit()
            app.logger.info(f"Stored certificate {certificate_id} in database for {lookup_column}={lookup_value}")
            
            cursor.close()
            conn.close()
            
            # Send certificate via email
            if candidate_email:
                try:
                    print(f"[DEBUG] Attempting to send certificate to {candidate_email}")
                    print(f"[DEBUG] PDF bytes type: {type(pdf_bytes)}, size: {len(pdf_bytes) if pdf_bytes else 0}")
                    # Call send_certificate_email with app context
                    with app.app_context():
                        result = send_certificate_email(candidate_email, candidate_name, pdf_bytes, certificate_id)
                    if result:
                        app.logger.info(f"✓ Certificate email sent to {candidate_email}")
                        print(f"✓ Certificate email sent to {candidate_email}")
                    else:
                        app.logger.warning(f"Failed to send certificate email to {candidate_email} - send function returned False")
                        print(f"❌ Certificate email send failed for {candidate_email}")
                except Exception as email_err:
                    app.logger.exception(f"Error sending certificate email to {candidate_email}: {email_err}")
                    print(f"❌ Exception sending certificate email: {email_err}")
                    import traceback
                    traceback.print_exc()
            else:
                app.logger.warning(f"No email found for candidate {candidate_id} - certificate not emailed")
                print(f"❌ No email found for candidate {candidate_id}")
        except Exception as e:
            app.logger.error(f"Failed to store certificate in database: {e}")
            import traceback
            traceback.print_exc()
            # Don't fail - certificate was still generated and stored on disk

        # Convert to base64 for response
        pdf_data = base64.b64encode(pdf_bytes).decode('utf-8')

        return jsonify({
            'success': True,
            'certificate_id': certificate_id,
            'pdf_data': pdf_data,
            'filename': f"{certificate_id}.pdf"
        })

    except FileNotFoundError as e:
        app.logger.error(f"[CERT ERROR] Template not found: {str(e)}")
        return jsonify({'success': False, 'error': f'Template not found: {str(e)}'}), 500
    except Exception as e:
        app.logger.exception(f"[CERT ERROR] {str(e)}")
        return jsonify({'success': False, 'error': f'Error: {str(e)}'}), 500


@app.route('/admin/api/download-certificate/<certificate_id>', methods=['GET'])
@login_required
def download_certificate(certificate_id):
    """Download a generated certificate from SWIZ_CERTI"""
    try:
        file_name = certificate_id.replace("/", "_") + ".pdf"
        cert_file_path = os.path.join(GENERATED_CERTS_PATH, file_name)
        
        if not os.path.exists(cert_file_path):
            # Try project-level copy
            project_copy = os.path.join(os.path.dirname(__file__), 'generated_certificates', file_name)
            if os.path.exists(project_copy):
                cert_file_path = project_copy
            else:
                app.logger.warning(f"Certificate not found at {cert_file_path} and no project copy at {project_copy}")
                return jsonify({'success': False, 'error': 'Certificate not found'}), 404
        
        return send_file(
            cert_file_path,
            as_attachment=True,
            download_name=f"{certificate_id}.pdf",
            mimetype='application/pdf'
        )
    except Exception as e:
        app.logger.error(f"Certificate download failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/admin/api/download-certificate-db/<usn>', methods=['GET'])
@login_required
def download_certificate_db(usn):
    """Download certificate from database for a candidate"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT certificate_pdf, certificate_id
            FROM Selected
            WHERE usn = %s AND certificate_pdf IS NOT NULL
            LIMIT 1
        """, (usn,))
        
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not result:
            return jsonify({'success': False, 'error': 'No stored certificate found'}), 404
        
        pdf_bytes = result.get('certificate_pdf')
        cert_id = result.get('certificate_id', 'certificate')
        
        if not pdf_bytes:
            return jsonify({'success': False, 'error': 'Certificate data is empty'}), 404
        
        filename = f"{cert_id}.pdf"
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        app.logger.error(f"Error downloading certificate from database: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== END CERTIFICATE GENERATION ====================

# ==================== OFFER LETTER GENERATION ====================

# ==================== OFFER LETTER HELPERS ====================

def format_date(dt):
    """Format date with ordinal suffix (e.g., 18th Nov 2025)"""
    d = dt.day
    suffix = "th" if 11 <= d <= 13 else {1:"st",2:"nd",3:"rd"}.get(d % 10, "th")
    return f"{d}{suffix} {dt.strftime('%b')} {dt.year}"

def get_monthwise_serial(month):
    """Get and increment serial number for the month"""
    from offer_letter_serial import get_serial
    return get_serial(month)

def generate_offer_pdf(name, usn, college, email, role, duration, intern_type):
    """
    Generate offer letter PDF with given parameters (from database).
    Returns: BytesIO object with PDF or None on failure
    """
    try:
        from reportlab.pdfgen import canvas
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.pdfbase.pdfmetrics import stringWidth
        from PyPDF2 import PdfReader, PdfWriter
        
        # Constants
        LEFT = 30
        RIGHT = 30
        LINE = 15
        GAP = 12
        TOP = 275
        F_SIZE = 12
        
        now = datetime.now()
        current_month = now.strftime("%b").upper()
        
        # Get serial - create if doesn't exist
        try:
            serial = get_monthwise_serial(current_month)
        except:
            serial = str(int(datetime.now().timestamp()) % 1000).zfill(3)
        
        ref_no = f"SZS/OFFR/{now.year}/{current_month}/{serial}"
        date_str = format_date(now)
        
        # Load template
        template_path = os.path.join('offer-letter-generator', 'offer_template', 'pdf_template.pdf')
        if not os.path.exists(template_path):
            raise Exception(f"Template not found at {template_path}")
        
        reader = PdfReader(open(template_path, "rb"))
        writer = PdfWriter()
        page = reader.pages[0]
        
        width = float(page.mediabox.width)
        height = float(page.mediabox.height)
        max_width = width - LEFT - RIGHT
        
        # Try to load fonts
        try:
            pdfmetrics.registerFont(TTFont("TNR", "offer-letter-generator/fonts/Times New Roman.ttf"))
            pdfmetrics.registerFont(TTFont("TNRB", "offer-letter-generator/fonts/Times New Roman Bold.ttf"))
            pdfmetrics.registerFont(TTFont("TNRI", "offer-letter-generator/fonts/Times New Roman Italic.ttf"))
            BODY, BOLD, ITALIC = "TNR", "TNRB", "TNRI"
        except:
            BODY, BOLD, ITALIC = "Times-Roman", "Times-Bold", "Times-Italic"
        
        buf = io.BytesIO()
        can = canvas.Canvas(buf, pagesize=(width, height))
        
        # ============ HEADER ============
        y = height - TOP
        can.setFont(BOLD, F_SIZE)
        can.drawString(LEFT, y, f"Ref. No.: {ref_no}")
        can.drawRightString(width - RIGHT, y, f"Date: {date_str}")
        
        # ============ TITLE ============
        y -= 40
        can.drawCentredString(width / 2, y, "INTERNSHIP OFFER LETTER")
        
        # ============ TO BLOCK ============
        y -= 50
        can.drawString(LEFT, y, "To,")
        y -= 20
        
        display_name = f"{name} ({usn})" if usn else name
        can.setFont(BODY, F_SIZE)
        can.drawString(LEFT, y, display_name); y -= 15
        can.drawString(LEFT, y, college); y -= 15
        can.drawString(LEFT, y, email); y -= 8
        
        can.setStrokeColorRGB(0.75, 0.75, 0.75)
        can.setLineWidth(1)
        can.line(LEFT, y, width - LEFT, y)
        y -= 25
        
        # ============ SUBJECT ============
        can.setFont(BOLD, F_SIZE)
        prefix = "Subject: Offer of Internship for the Role of "
        can.drawString(LEFT, y, prefix)
        can.drawString(LEFT + stringWidth(prefix, BOLD, F_SIZE), y, role)
        y -= 30
        
        # ============ SALUTATION ============
        can.setFont(BODY, F_SIZE)
        can.drawString(LEFT, y, f"Dear {name},")
        y -= 30
        
        # ============ BOLD & ITALIC PATTERNS ============
        bold_duration_trial = re.compile(rf"{re.escape(duration)}", re.IGNORECASE)
        bold_hands_on = re.compile(r"hands-on\s+project\s+experience", re.IGNORECASE)
        bold_swizo = re.compile(re.escape("Swizosoft (OPC) Private Limited"), re.IGNORECASE)
        bold_team = re.compile(re.escape("Team Swizosoft (OPC) Private Limited"), re.IGNORECASE)
        bold_industry = re.compile(r"industry-ready\s+skills", re.IGNORECASE)
        bold_role = re.compile(re.escape(role), re.IGNORECASE)
        bold_intern_type = re.compile(re.escape(intern_type), re.IGNORECASE)
        bold_trial = re.compile(r"gain\s+hands-on\s+project", re.IGNORECASE)
        
        BOLD_PATTERNS = [
            bold_duration_trial,
            bold_hands_on,
            bold_industry,
            bold_team,
            bold_swizo,
            bold_intern_type,
            bold_trial,
            bold_role,
        ]
        
        ITALIC_PHRASE = "real-time project execution"
        
        # ============ SEGMENT BUILDER ============
        def build_segments(words):
            txt = " ".join(words)
            segs = []
            pos = 0
            L = len(txt)
            
            while pos < L:
                earliest = None
                
                # Check for italic
                idx = txt.lower().find(ITALIC_PHRASE.lower(), pos)
                if idx != -1:
                    earliest = (idx, idx+len(ITALIC_PHRASE), ITALIC)
                
                # Check for bold patterns
                for rx in BOLD_PATTERNS:
                    m = rx.search(txt, pos)
                    if m:
                        s,e = m.start(), m.end()
                        if earliest is None or s < earliest[0]:
                            earliest = (s,e,BOLD)
                
                if not earliest:
                    rest = txt[pos:].strip()
                    if rest:
                        for w in rest.split():
                            segs.append((w, BODY))
                    break
                
                s,e,font = earliest
                before = txt[pos:s].strip()
                if before:
                    for w in before.split():
                        segs.append((w,BODY))
                
                special = txt[s:e]
                for w in special.split():
                    segs.append((w,font))
                
                pos = e
            
            return segs
        
        # ============ JUSTIFIED DRAW ============
        def draw_justified(segs, yy):
            if len(segs) == 1:
                w,f = segs[0]
                can.setFont(f, F_SIZE)
                can.drawString(LEFT, yy, w)
                return
            
            total = sum(stringWidth(w,f,F_SIZE) for w,f in segs)
            rem = max_width - total
            gaps = len(segs) - 1
            gap = rem / gaps if gaps > 0 else 0
            
            x = LEFT
            for i,(w,f) in enumerate(segs):
                can.setFont(f, F_SIZE)
                can.drawString(x, yy, w)
                x += stringWidth(w,f,F_SIZE)
                if i != len(segs)-1:
                    x += gap
        
        # ============ PARAGRAPH ENGINE ============
        def paragraph(text):
            nonlocal y
            text = text.replace("\r","")
            
            parts=[]
            for line in text.split("\n"):
                words = line.split()
                if words:
                    parts.extend(words)
                parts.append("\n")
            
            if parts and parts[-1] == "\n":
                parts.pop()
            
            words = parts
            curr=[]
            
            while words:
                t = words.pop(0)
                
                if t == "\n":
                    if curr:
                        seg = build_segments(curr)
                        draw_justified(seg, y)
                        y -= LINE
                        curr=[]
                    else:
                        y -= LINE
                    continue
                
                test = curr + [t]
                test_line = " ".join(test)
                
                if stringWidth(test_line, BODY, F_SIZE) <= max_width:
                    curr = test
                    if not words:
                        can.setFont(BODY,F_SIZE)
                        can.drawString(LEFT,y," ".join(curr))
                        y -= LINE + GAP
                        return
                else:
                    if curr:
                        seg = build_segments(curr)
                        draw_justified(seg, y)
                        y -= LINE
                    curr=[t]
            
            y -= GAP
        
        # ============ PARAGRAPHS ============
        paragraph("Congratulations!")
        
        paragraph(
            f"We are pleased to offer you the position of {role} at Swizosoft (OPC) Private Limited for a period of {duration}."
        )
        
        paragraph(
            f"This internship is a {intern_type} designed to help students gain hands-on project\n"
            " experience and develop industry-ready skills in their respective domains. You will be assigned "
            "project-based tasks to work on from your own location, under the guidance of our mentors and "
            "coordinators."
        )
        
        paragraph(
            "Our goal is to ensure that you learn through real-time project execution rather than classroom "
            "sessions — allowing you to experience how actual software projects are managed in the IT industry."
        )
        
        paragraph(
            "We are excited to have you join Team Swizosoft (OPC) Private Limited, and we look forward to your "
            "active contribution, learning, and growth throughout this journey."
        )
        
        # ============ SIGNATURE ============
        y -= 10
        can.setFont(BOLD, F_SIZE)
        can.drawString(LEFT, y, "Mr. Aditya Madhukar Bhat")
        y -= 18
        can.drawString(LEFT, y, "Director, Swizosoft (OPC) Private Limited")
        
        # ============ MERGE PDF ============
        can.save()
        buf.seek(0)
        overlay = PdfReader(buf)
        page.merge_page(overlay.pages[0])
        
        writer.add_page(page)
        for i in range(1, len(reader.pages)):
            writer.add_page(reader.pages[i])
        
        # Return BytesIO with PDF
        output = io.BytesIO()
        writer.write(output)
        output.seek(0)
        
        return output, ref_no
        
    except Exception as e:
        app.logger.error(f"Error generating offer PDF: {e}")
        import traceback
        traceback.print_exc()
        return None, None


@app.route('/admin/api/generate-offer-letter/<usn>', methods=['GET', 'POST'])
@login_required
def admin_generate_offer_letter(usn):
    """Generate and download offer letter for a selected candidate"""
    try:
        # Get candidate from Selected table
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT name, usn, email, college, domain, roles, candidate_id, mode_of_internship
            FROM Selected
            WHERE usn = %s
            LIMIT 1
        """, (usn,))
        
        candidate = cursor.fetchone()
        
        if not candidate:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'error': 'Candidate not found in Selected table'}), 404
        
        # Extract data from database
        name = candidate.get('name', '')
        email = candidate.get('email', '')
        college = candidate.get('college', '')
        domain = candidate.get('domain', '')
        roles = candidate.get('roles', '')
        
        # If roles is empty, construct from domain
        if not roles and domain:
            role = f"{domain} Intern"
        elif roles:
            role = roles
        else:
            role = "Intern"
        
        internship_type = candidate.get('mode_of_internship', 'remote-based opportunity')
        
        # Generate PDF using the working function
        output, ref_no = generate_offer_pdf(name, usn, college, email, role, '3 months', internship_type)
        
        if not output or not ref_no:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'error': 'Failed to generate offer letter'}), 500
        
        # Get PDF bytes
        pdf_bytes = output.getvalue()
        
        # Store PDF in database
        try:
            update_sql = """UPDATE Selected SET 
                offer_letter_pdf = %s,
                offer_letter_reference = %s,
                offer_letter_generated_date = NOW()
                WHERE usn = %s"""
            
            cursor.execute(update_sql, (pdf_bytes, ref_no, usn))
            conn.commit()
            app.logger.info(f"Stored offer letter PDF in database for {usn} with ref {ref_no}")
            
            # Send offer letter via email
            try:
                print(f"[DEBUG] Manually sending offer letter email to {email}")
                print(f"[DEBUG] PDF bytes type: {type(pdf_bytes)}, size: {len(pdf_bytes) if pdf_bytes else 0}")
                result = send_offer_letter_email(email, name, pdf_bytes, ref_no)
                if result:
                    app.logger.info(f"✓ Offer letter email sent to {email}")
                    print(f"✓ Offer letter email sent to {email}")
                else:
                    app.logger.warning(f"Failed to send offer letter email to {email}")
                    print(f"❌ Offer letter email send failed for {email}")
            except Exception as email_err:
                app.logger.exception(f"Error sending offer letter email: {email_err}")
                print(f"❌ Exception: {email_err}")
                import traceback
                traceback.print_exc()
        except Exception as e:
            app.logger.error(f"Failed to store PDF in database: {e}")
            conn.rollback()
        finally:
            cursor.close()
            conn.close()
        
        # Return PDF as download
        filename = f"SZS_OFFR_{ref_no.replace('/', '_')}.pdf"
        return send_file(
            output,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
            
    except Exception as e:
        app.logger.error(f"Error in generate-offer-letter: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/admin/api/download-offer-letter/<usn>', methods=['GET'])
@login_required
def admin_download_offer_letter(usn):
    """Download offer letter from database"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT offer_letter_pdf, offer_letter_reference
            FROM Selected
            WHERE usn = %s AND offer_letter_pdf IS NOT NULL
            LIMIT 1
        """, (usn,))
        
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not result:
            return jsonify({'success': False, 'error': 'No stored offer letter found'}), 404
        
        pdf_bytes = result.get('offer_letter_pdf')
        ref_no = result.get('offer_letter_reference', 'offer_letter')
        
        if not pdf_bytes:
            return jsonify({'success': False, 'error': 'Offer letter data is empty'}), 404
        
        filename = f"SZS_OFFR_{ref_no.replace('/', '_')}.pdf"
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        app.logger.error(f"Error downloading offer letter: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/admin/api/offer-letter-status', methods=['GET'])
@login_required
def admin_offer_letter_status():
    """Get offer letter generation status for all candidates"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT usn, name, offer_letter_reference, offer_letter_generated_date,
                   IF(offer_letter_pdf IS NOT NULL, 'generated', 'pending') as status
            FROM Selected
            ORDER BY offer_letter_generated_date DESC
        """)
        
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        
        offers = []
        for row in results:
            offers.append({
                'usn': row.get('usn'),
                'name': row.get('name'),
                'reference': row.get('offer_letter_reference'),
                'generated_date': row.get('offer_letter_generated_date'),
                'status': row.get('status')
            })
        
        return jsonify({'success': True, 'offers': offers}), 200
        
    except Exception as e:
        app.logger.error(f"Error getting offer letter status: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== END OFFER LETTER GENERATION ====================

if __name__ == '__main__':
    # Ensure a secret key exists for session support
    if not app.secret_key:
        app.secret_key = app.config.get('SECRET_KEY') or 'dev-secret-change-me'
    
    # Run the Flask development server
    app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)
