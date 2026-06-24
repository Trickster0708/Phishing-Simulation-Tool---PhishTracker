import sqlite3
import os

DB_PATH = 'test_lock.db'
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)

conn1 = sqlite3.connect(DB_PATH)
conn1.execute("CREATE TABLE IF NOT EXISTS test (id INTEGER PRIMARY KEY, val TEXT)")
conn1.execute("INSERT INTO test (val) VALUES ('hello')")
conn1.commit()

# Start connection 1 (reads)
conn1.row_factory = sqlite3.Row
r = conn1.execute("SELECT * FROM test").fetchone()
print("Read value from conn1:", r['val'])

# Try connection 2 (writes)
try:
    conn2 = sqlite3.connect(DB_PATH)
    conn2.execute("INSERT INTO test (val) VALUES ('world')")
    conn2.commit()
    conn2.close()
    print("Write to conn2 succeeded!")
except Exception as e:
    print("Write to conn2 failed:", e)

# Finish connection 1
conn1.execute("UPDATE test SET val = 'updated' WHERE id = 1")
conn1.commit()
conn1.close()
print("Conn1 updated and committed!")

if os.path.exists(DB_PATH):
    os.remove(DB_PATH)
