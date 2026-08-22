def run_query(sql):
    cursor.execute(sql)
    return cursor.fetchall()


from typing import Any

cursor: Any = None  # stub: this fixture is scanned structurally, never imported/executed
