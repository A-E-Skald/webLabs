
import sqlite3
from pathlib import Path
p = Path('app')/'instance'/'app.db'
print("trying to open:", p.resolve())
conn = sqlite3.connect(str(p.resolve()))
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
print(cur.fetchall())
conn.close()
print("ok")

