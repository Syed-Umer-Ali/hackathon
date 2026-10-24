import pandas as pd, sqlite3
con = sqlite3.connect("hr.db")
l = pd.read_sql("SELECT * FROM raw_leave_requests LIMIT 3", con).drop(columns=["_row_hash", "_source_file", "_loaded_at"])
print(l.columns.tolist())
for i, r in l.iterrows():
    print(r.to_dict())