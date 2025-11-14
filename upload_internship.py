#!/usr/bin/env python
"""
Utility script to upload internship records and files to the database
Usage: python upload_internship.py
"""

import MySQLdb
import os
import sys
from pathlib import Path

# Database configuration
DB_CONFIG = {
    'host': 'srv1128.hstgr.io',
    'user': 'u973091162_swizosoft_int',
    'passwd': 'Internship@Swizosoft1',
    'db': 'u973091162_internship_swi'
}

def connect_db():
    """Connect to the database"""
    try:
        conn = MySQLdb.connect(**DB_CONFIG)
        return conn
    except MySQLdb.Error as e:
        print(f"Error connecting to database: {e}")
        return None

def upload_internship(table_name, name, usn, resume_file=None, project_file=None, id_card_file=None):
    """
    Upload an internship record to the database
    
    Args:
        table_name: 'free_internship' or 'paid_internship'
        name: Applicant's name
        usn: Unique Student Number
        resume_file: Path to resume PDF
        project_file: Path to project PDF
        id_card_file: Path to ID card image
    """
    conn = connect_db()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        # Read files
        resume_data = None
        project_data = None
        id_card_data = None
        
        if resume_file and os.path.exists(resume_file):
            with open(resume_file, 'rb') as f:
                resume_data = f.read()
            print(f"✓ Loaded resume: {os.path.basename(resume_file)} ({len(resume_data)} bytes)")
        
        if project_file and os.path.exists(project_file):
            with open(project_file, 'rb') as f:
                project_data = f.read()
            print(f"✓ Loaded project: {os.path.basename(project_file)} ({len(project_data)} bytes)")
        
        if id_card_file and os.path.exists(id_card_file):
            with open(id_card_file, 'rb') as f:
                id_card_data = f.read()
            print(f"✓ Loaded ID card: {os.path.basename(id_card_file)} ({len(id_card_data)} bytes)")
        
        # Insert into database
        sql = f"""
            INSERT INTO {table_name} (name, usn, resume, project, id_card)
            VALUES (%s, %s, %s, %s, %s)
        """
        
        cursor.execute(sql, (name, usn, resume_data, project_data, id_card_data))
        conn.commit()
        
        print(f"✓ Successfully uploaded {name} ({usn}) to {table_name}")
        return True
        
    except MySQLdb.Error as e:
        print(f"✗ Database error: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

def list_internships(table_name):
    """List all records in a table"""
    conn = connect_db()
    if not conn:
        return
    
    try:
        cursor = conn.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute(f"SELECT id, name, usn FROM {table_name}")
        records = cursor.fetchall()
        
        print(f"\n📋 Records in {table_name}:")
        print("-" * 50)
        for record in records:
            print(f"ID: {record['id']}, Name: {record['name']}, USN: {record['usn']}")
        print("-" * 50)
        print(f"Total: {len(records)} records\n")
        
    except MySQLdb.Error as e:
        print(f"Error: {e}")
    finally:
        cursor.close()
        conn.close()

def delete_internship(table_name, usn):
    """Delete an internship record by USN"""
    conn = connect_db()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        cursor.execute(f"DELETE FROM {table_name} WHERE usn = %s", (usn,))
        conn.commit()
        
        if cursor.rowcount > 0:
            print(f"✓ Successfully deleted record with USN: {usn}")
            return True
        else:
            print(f"✗ No record found with USN: {usn}")
            return False
            
    except MySQLdb.Error as e:
        print(f"Error: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

def batch_upload(directory, table_name):
    """
    Batch upload from a directory structure:
    directory/
        student1/
            resume.pdf
            project.pdf
            id_card.jpg
        student2/
            ...
    """
    print(f"\n📤 Starting batch upload from {directory}")
    print("-" * 50)
    
    if not os.path.isdir(directory):
        print(f"✗ Directory not found: {directory}")
        return
    
    count = 0
    for student_dir in os.listdir(directory):
        student_path = os.path.join(directory, student_dir)
        
        if not os.path.isdir(student_path):
            continue
        
        # Parse student name and USN from directory name (format: "Name_USN")
        parts = student_dir.rsplit('_', 1)
        if len(parts) != 2:
            print(f"⚠ Skipping {student_dir} - use format 'Name_USN'")
            continue
        
        name, usn = parts
        
        # Find files
        resume_file = None
        project_file = None
        id_card_file = None
        
        for file in os.listdir(student_path):
            file_path = os.path.join(student_path, file)
            if file.lower().startswith('resume'):
                resume_file = file_path
            elif file.lower().startswith('project'):
                project_file = file_path
            elif file.lower().startswith('id'):
                id_card_file = file_path
        
        # Upload
        if upload_internship(table_name, name, usn, resume_file, project_file, id_card_file):
            count += 1
        print()
    
    print("-" * 50)
    print(f"✓ Batch upload complete! {count} records uploaded.")

def main():
    """Main menu"""
    while True:
        print("\n" + "="*50)
        print("SWIZOSOFT - Internship Database Upload Tool")
        print("="*50)
        print("\n1. Upload single internship (FREE)")
        print("2. Upload single internship (PAID)")
        print("3. List all FREE internships")
        print("4. List all PAID internships")
        print("5. Delete internship record")
        print("6. Batch upload from directory")
        print("7. Test database connection")
        print("8. Exit")
        
        choice = input("\nEnter your choice (1-8): ").strip()
        
        if choice == '1':
            name = input("Enter name: ").strip()
            usn = input("Enter USN: ").strip()
            resume = input("Enter resume file path (or press Enter to skip): ").strip()
            project = input("Enter project file path (or press Enter to skip): ").strip()
            id_card = input("Enter ID card file path (or press Enter to skip): ").strip()
            
            upload_internship('free_internship', name, usn, resume or None, project or None, id_card or None)
        
        elif choice == '2':
            name = input("Enter name: ").strip()
            usn = input("Enter USN: ").strip()
            resume = input("Enter resume file path (or press Enter to skip): ").strip()
            project = input("Enter project file path (or press Enter to skip): ").strip()
            id_card = input("Enter ID card file path (or press Enter to skip): ").strip()
            
            upload_internship('paid_internship', name, usn, resume or None, project or None, id_card or None)
        
        elif choice == '3':
            list_internships('free_internship')
        
        elif choice == '4':
            list_internships('paid_internship')
        
        elif choice == '5':
            table = input("Enter table (free_internship/paid_internship): ").strip()
            usn = input("Enter USN to delete: ").strip()
            delete_internship(table, usn)
        
        elif choice == '6':
            directory = input("Enter directory path: ").strip()
            table = input("Enter table (free_internship/paid_internship): ").strip()
            batch_upload(directory, table)
        
        elif choice == '7':
            conn = connect_db()
            if conn:
                print("✓ Database connection successful!")
                conn.close()
            else:
                print("✗ Database connection failed!")
        
        elif choice == '8':
            print("Goodbye!")
            break
        
        else:
            print("Invalid choice. Please try again.")

if __name__ == '__main__':
    main()
