import pandas as pd, sqlite3
con = sqlite3.connect("hr.db")

d = pd.read_sql("SELECT * FROM raw_departments", con)
print(d.drop(columns=["_row_hash", "_source_file", "_loaded_at"]).to_string())

h = pd.read_sql("SELECT * FROM raw_employment_history", con)
print(h.columns.tolist())
print(h.head(8).drop(columns=["_row_hash", "_source_file", "_loaded_at"]).to_string())