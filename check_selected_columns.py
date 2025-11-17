import pymysql
from config import Config

conn = pymysql.connect(
    host=Config.MYSQL_HOST,
    user=Config.MYSQL_USER,
    password=Config.MYSQL_PASSWORD,
    database=Config.MYSQL_DB,
    charset='utf8mb4',
    cursorclass=pymysql.cursors.DictCursor,
)
cursor = conn.cursor()

# Check Selected table structure
cursor.execute('DESC Selected')
columns = cursor.fetchall()

print('Selected Table Columns:')
print('='*80)
for col in columns:
    print(f"{col['Field']:35} | {col['Type']:25} | {col['Key']}")

cursor.close()
conn.close()
