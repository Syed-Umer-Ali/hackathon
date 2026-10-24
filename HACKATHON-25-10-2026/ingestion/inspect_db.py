import sqlite3
con = sqlite3.connect("hr.db")
tables = [r[0] for r in con.execute(
    "SELECT name FROM sqlite_master WHERE type='table' AND (name LIKE 'dim_%' OR name LIKE 'fact_%' OR name LIKE 'stg_%') ORDER BY name")]
for t in tables:
    cols = [c[1] for c in con.execute(f"PRAGMA table_info({t})")]
    n = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    print(f"{t} ({n} rows): {', '.join(cols)}")
print()
for t in ["raw_overtime_requests", "raw_payroll_lines"]:
    cols = [c[1] for c in con.execute(f"PRAGMA table_info({t})")]
    print(t, ":", ", ".join(cols))
    print(con.execute(f"SELECT * FROM {t} LIMIT 3").fetchall())