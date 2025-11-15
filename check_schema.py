import pymysql

conn = pymysql.connect(host='srv1128.hstgr.io', user='u973091162_swizosoft_int', password='Internship@Swizosoft1', database='u973091162_internship_swi', cursorclass=pymysql.cursors.DictCursor)
cursor = conn.cursor()
cursor.execute('DESCRIBE free_internship_application')
cols = cursor.fetchall()
print("free_internship_application columns:")
for c in cols:
    print(f"  {c['Field']}: {c['Type']}")
conn.close()
