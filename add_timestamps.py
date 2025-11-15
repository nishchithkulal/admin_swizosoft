"""
Add missing columns to approved_candidates table
"""
import pymysql
from config import get_config

def add_missing_columns():
    """Add created_at and updated_at columns if they don't exist"""
    config = get_config()
    
    host = getattr(config, 'MYSQL_HOST', None)
    user = getattr(config, 'MYSQL_USER', None)
    password = getattr(config, 'MYSQL_PASSWORD', None)
    db = getattr(config, 'MYSQL_DB', None)
    
    print(f"Connecting to {host}...")
    
    try:
        conn = pymysql.connect(
            host=host,
            user=user,
            password=password,
            database=db,
            charset='utf8mb4'
        )
        cursor = conn.cursor()
        
        # Add created_at and updated_at columns
        print("\nAdding timestamp columns...")
        
        # Check if columns exist before adding
        cursor.execute("""
            SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME='approved_candidates' AND COLUMN_NAME IN ('created_at', 'updated_at')
        """)
        
        existing_cols = {row[0] for row in cursor.fetchall()}
        
        if 'created_at' not in existing_cols:
            print("  Adding created_at column...")
            cursor.execute("""
                ALTER TABLE approved_candidates 
                ADD COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            """)
            print("  ✓ created_at added")
        else:
            print("  ✓ created_at already exists")
        
        if 'updated_at' not in existing_cols:
            print("  Adding updated_at column...")
            cursor.execute("""
                ALTER TABLE approved_candidates 
                ADD COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            """)
            print("  ✓ updated_at added")
        else:
            print("  ✓ updated_at already exists")
        
        conn.commit()
        
        # Show table structure
        print("\n✓ Table structure updated successfully!")
        print("\nFinal table structure:")
        cursor.execute("DESCRIBE approved_candidates")
        columns = cursor.fetchall()
        for col in columns:
            print(f"  - {col[0]}: {col[1]}")
        
        cursor.close()
        conn.close()
        return True
        
    except pymysql.Error as e:
        print(f"✗ Database error: {e}")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

if __name__ == '__main__':
    import sys
    success = add_missing_columns()
    sys.exit(0 if success else 1)
