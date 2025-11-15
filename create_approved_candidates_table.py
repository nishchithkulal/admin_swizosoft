"""
Script to create the approved_candidates table in MySQL
"""
import pymysql
from urllib.parse import unquote
from config import get_config

def create_approved_candidates_table():
    """Create the approved_candidates table"""
    config = get_config()
    
    # Get database connection details
    host = getattr(config, 'MYSQL_HOST', None)
    user = getattr(config, 'MYSQL_USER', None)
    password = getattr(config, 'MYSQL_PASSWORD', None)
    db = getattr(config, 'MYSQL_DB', None)
    
    print(f"Connecting to {host} as {user}...")
    
    try:
        conn = pymysql.connect(
            host=host,
            user=user,
            password=password,
            database=db,
            charset='utf8mb4'
        )
        cursor = conn.cursor()
        
        # Create the table
        sql = """
        CREATE TABLE IF NOT EXISTS approved_candidates (
            usn VARCHAR(50) PRIMARY KEY,
            application_id INT UNIQUE NOT NULL,
            name VARCHAR(255) NOT NULL,
            email VARCHAR(255) NOT NULL,
            phone_number VARCHAR(20) NOT NULL,
            year VARCHAR(50),
            qualification VARCHAR(255),
            branch VARCHAR(255),
            college VARCHAR(255),
            domain VARCHAR(255),
            mode_of_interview VARCHAR(20) DEFAULT 'online',
            resume_name VARCHAR(255),
            resume_content MEDIUMBLOB,
            project_document_name VARCHAR(255),
            project_document_content MEDIUMBLOB,
            id_proof_name VARCHAR(255),
            id_proof_content MEDIUMBLOB,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_application_id (application_id),
            INDEX idx_created_at (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """
        
        cursor.execute(sql)
        conn.commit()
        
        print("✓ Table 'approved_candidates' created successfully!")
        
        # Verify the table exists
        cursor.execute("DESCRIBE approved_candidates")
        columns = cursor.fetchall()
        print(f"\n✓ Table structure ({len(columns)} columns):")
        for col in columns:
            print(f"  - {col[0]}: {col[1]}")
        
        cursor.close()
        conn.close()
        print("\n✓ Database connection closed.")
        
    except pymysql.Error as e:
        print(f"✗ Database error: {e}")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False
    
    return True

if __name__ == '__main__':
    success = create_approved_candidates_table()
    exit(0 if success else 1)
