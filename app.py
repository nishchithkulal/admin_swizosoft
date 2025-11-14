from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_file
from flask_mysqldb import MySQL
import MySQLdb.cursors
import io
import os
from functools import wraps

app = Flask(__name__)

# Load configuration
from config import get_config
app.config.from_object(get_config())

# Initialize MySQL
mysql = MySQL(app)

# Admin credentials from config
ADMIN_USERNAME = app.config.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = app.config.get('ADMIN_PASSWORD', 'admin123')

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Resolve internship table names to support both naming conventions
def _resolve_table_name(base_name):
    try:
        cursor = mysql.connection.cursor()
        db = app.config.get('MYSQL_DB')
        candidates = [base_name, f"{base_name}_application"]
        for t in candidates:
            cursor.execute(
                "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=%s AND table_name=%s",
                (db, t)
            )
            row = cursor.fetchone()
            if row and row[0] > 0:
                cursor.close()
                return t
        cursor.close()
    except Exception:
        pass
    return base_name

# Cache resolved names
RESOLVED_FREE_TABLE = _resolve_table_name('free_internship')
RESOLVED_PAID_TABLE = _resolve_table_name('paid_internship')

@app.route('/')
def index():
    if 'admin_logged_in' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        
        # Check credentials
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            session.permanent = True
            return redirect(url_for('dashboard'))
        else:
            error = 'Invalid username or password'
            return render_template('login.html', error=error)
    
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

def get_internships():
    try:
        internship_type = request.args.get('type', 'free')  # 'free' or 'paid'
        
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        if internship_type == 'paid':
            table = RESOLVED_PAID_TABLE
        else:
            table = RESOLVED_FREE_TABLE
        query = f"SELECT id, name, usn FROM {table}"
        try:
            cursor.execute(query)
            internships = cursor.fetchall()
        except Exception:
            # try alternate table name
            alt_table = table + '_application' if not table.endswith('_application') else table.replace('_application', '')
            alt_query = f"SELECT id, name, usn FROM {alt_table}"
            cursor.execute(alt_query)
            internships = cursor.fetchall()
        cursor.close()
        return jsonify({'success': True, 'data': internships})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

def get_resume(internship_id):
    try:
        internship_type = request.args.get('type', 'free')
        
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        
        if internship_type == 'paid':
            table = RESOLVED_PAID_TABLE
        else:
            table = RESOLVED_FREE_TABLE
        query = f"SELECT resume FROM {table} WHERE id = %s"
        
        try:
            cursor.execute(query, (internship_id,))
            result = cursor.fetchone()
        except Exception:
            alt_table = table + '_application' if not table.endswith('_application') else table.replace('_application', '')
            alt_query = f"SELECT resume FROM {alt_table} WHERE id = %s"
            cursor.execute(alt_query, (internship_id,))
            result = cursor.fetchone()
        cursor.close()
        
        if result and result['resume']:
            file_data = result['resume']
            return send_file(
                io.BytesIO(file_data),
                mimetype='application/octet-stream',
                as_attachment=True,
                download_name=f'resume_{internship_id}.pdf'
            )
        else:
            return jsonify({'error': 'Resume not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def get_project(internship_id):
    try:
        internship_type = request.args.get('type', 'free')
        
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        
        if internship_type == 'paid':
            table = RESOLVED_PAID_TABLE
        else:
            table = RESOLVED_FREE_TABLE
        query = f"SELECT project FROM {table} WHERE id = %s"
        
        try:
            cursor.execute(query, (internship_id,))
            result = cursor.fetchone()
        except Exception:
            alt_table = table + '_application' if not table.endswith('_application') else table.replace('_application', '')
            alt_query = f"SELECT project FROM {alt_table} WHERE id = %s"
            cursor.execute(alt_query, (internship_id,))
            result = cursor.fetchone()
        cursor.close()
        
        if result and result['project']:
            file_data = result['project']
            return send_file(
                io.BytesIO(file_data),
                mimetype='application/octet-stream',
                as_attachment=True,
                download_name=f'project_{internship_id}.pdf'
            )
        else:
            return jsonify({'error': 'Project not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def get_id_card(internship_id):
    try:
        internship_type = request.args.get('type', 'free')
        
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        
        if internship_type == 'paid':
            table = RESOLVED_PAID_TABLE
        else:
            table = RESOLVED_FREE_TABLE
        query = f"SELECT id_card FROM {table} WHERE id = %s"
        
        try:
            cursor.execute(query, (internship_id,))
            result = cursor.fetchone()
        except Exception:
            alt_table = table + '_application' if not table.endswith('_application') else table.replace('_application', '')
            alt_query = f"SELECT id_card FROM {alt_table} WHERE id = %s"
            cursor.execute(alt_query, (internship_id,))
            result = cursor.fetchone()
        cursor.close()
        
        if result and result['id_card']:
            file_data = result['id_card']
            return send_file(
                io.BytesIO(file_data),
                mimetype='application/octet-stream',
                as_attachment=True,
                download_name=f'id_card_{internship_id}.jpg'
            )
        else:
            return jsonify({'error': 'ID card not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/view-file/<int:internship_id>/<file_type>', methods=['GET'])
@login_required
def view_file(internship_id, file_type):
    """
    View file in browser instead of downloading
    file_type: resume, project, id_card
    """
    try:
        internship_type = request.args.get('type', 'free')
        
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        
        # Map file types to column names
        column_map = {
            'resume': 'resume',
            'project': 'project',
            'id_card': 'id_card'
        }
        
        if file_type not in column_map:
            return jsonify({'error': 'Invalid file type'}), 400
        
        column = column_map[file_type]
        
        if internship_type == 'paid':
            query = f"SELECT {column} FROM paid_internship WHERE id = %s"
        else:
            query = f"SELECT {column} FROM free_internship WHERE id = %s"
        
        cursor.execute(query, (internship_id,))
        result = cursor.fetchone()
        cursor.close()
        
        if result and result[column]:
            file_data = result[column]
            # Determine MIME type based on file extension or content
            mime_types = {
                'resume': 'application/pdf',
                'project': 'application/pdf',
                'id_card': 'image/jpeg'
            }
            return send_file(
                io.BytesIO(file_data),
                mimetype=mime_types.get(file_type, 'application/octet-stream'),
                as_attachment=False
            )
        else:
            return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
