#!/usr/bin/env python3
"""
Database initialization script for approved_candidates table
Run this script to create the table in the database
"""
import sys
import os
from urllib.parse import quote_plus
from flask import Flask
from config import get_config
from models import db, ApprovedCandidate

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def init_db():
    """Initialize the database and create tables"""
    # Create Flask app
    app = Flask(__name__)
    app.config.from_object(get_config())
    
    # Configure SQLAlchemy to use PyMySQL with correct connection string
    mysql_user = app.config['MYSQL_USER']
    mysql_password = app.config['MYSQL_PASSWORD']
    mysql_host = app.config['MYSQL_HOST']
    mysql_db = app.config['MYSQL_DB']
    
    # URL-encode the password to handle special characters
    encoded_password = quote_plus(mysql_password)
    
    app.config['SQLALCHEMY_DATABASE_URI'] = (
        f"mysql+pymysql://{mysql_user}:{encoded_password}@"
        f"{mysql_host}/{mysql_db}?charset=utf8mb4"
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'connect_args': {
            'charset': 'utf8mb4'
        }
    }
    
    # Initialize db
    db.init_app(app)
    
    with app.app_context():
        try:
            # Create all tables
            db.create_all()
            print("✓ Database initialized successfully!")
            print(f"✓ Table 'approved_candidates' created in database '{app.config['MYSQL_DB']}'")
            print("\nTable schema:")
            print("  - usn (VARCHAR(50), PRIMARY KEY)")
            print("  - application_id (INT, UNIQUE)")
            print("  - name (VARCHAR(255))")
            print("  - email (VARCHAR(255))")
            print("  - phone_number (VARCHAR(20))")
            print("  - year (VARCHAR(50))")
            print("  - qualification (VARCHAR(255))")
            print("  - branch (VARCHAR(255))")
            print("  - college (VARCHAR(255))")
            print("  - domain (VARCHAR(255))")
            print("  - mode_of_interview (ENUM('online', 'offline'))")
            print("  - resume_name (VARCHAR(255))")
            print("  - resume_content (LONGBLOB/MEDIUMBLOB)")
            print("  - project_document_name (VARCHAR(255))")
            print("  - project_document_content (LONGBLOB/MEDIUMBLOB)")
            print("  - id_proof_name (VARCHAR(255))")
            print("  - id_proof_content (LONGBLOB/MEDIUMBLOB)")
            print("  - created_at (DATETIME)")
            print("  - updated_at (DATETIME)")
        except Exception as e:
            print(f"✗ Error creating database: {e}")
            return False
    
    return True

if __name__ == '__main__':
    success = init_db()
    sys.exit(0 if success else 1)
