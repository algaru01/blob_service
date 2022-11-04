import sqlite3

con = sqlite3.connect('./dataBase.db')

cur = con.cursor()

cur.execute("SELECT * FROM user")
r = cur.fetchall()
print(r)

cur.execute("SELECT * FROM blob")
r = cur.fetchall()
print(r)

cur.execute("SELECT * FROM writable_by")
r = cur.fetchall()
print(r)

cur.execute("SELECT * FROM readable_by")
r = cur.fetchall()
print(r)

result = cur.execute("SELECT * FROM blob WHERE blob_id = ?", ('813',))
print(result)