import pandas as pd, sqlite3
con = sqlite3.connect("hr.db")
M = ["_row_hash", "_source_file", "_loaded_at"]

p = pd.read_sql("SELECT punch_id, device_id, device_user_id, punch_time FROM raw_biometric_punches", con)
dm = pd.read_sql("SELECT device_id, device_user_id, emp_id FROM raw_device_mapping", con)
print("punches:", len(p), "| mapping dup keys:", dm.duplicated(["device_id", "device_user_id"]).sum())

m = p.merge(dm, on=["device_id", "device_user_id"], how="left")
print("unmapped:", m["emp_id"].isna().sum())
print(m[m["emp_id"].isna()]["device_user_id"].value_counts().head(5))

m["t"] = pd.to_datetime(m["punch_time"])
print("range:", m["t"].min(), "to", m["t"].max())
print(pd.crosstab(m["t"].dt.hour, m["device_id"]))

print(pd.read_sql("SELECT * FROM raw_shifts", con).drop(columns=M).to_string())
print(pd.read_sql("SELECT * FROM raw_shift_roster LIMIT 5", con).drop(columns=M).to_string())
print(pd.read_sql("SELECT * FROM raw_holidays", con).drop(columns=M).to_string())