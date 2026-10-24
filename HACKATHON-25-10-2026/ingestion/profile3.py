import pandas as pd, sqlite3
con = sqlite3.connect("hr.db")
M = ["_row_hash", "_source_file", "_loaded_at"]

dm = pd.read_sql("SELECT * FROM raw_device_mapping", con).drop(columns=M)
print(dm.columns.tolist()); print(dm.head(5).to_string())
print("rows:", len(dm))

p = pd.read_sql("SELECT * FROM raw_biometric_punches LIMIT 200000", con).drop(columns=M)
print(p.columns.tolist()); print(p.head(8).to_string())
for c in p.columns:
    print(c, "unique:", p[c].nunique(), "| blanks:", (p[c] == "").sum())