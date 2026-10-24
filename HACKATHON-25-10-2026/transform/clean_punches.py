import pandas as pd, sqlite3

con = sqlite3.connect("hr.db")
CLOCK_OFFSET_HOURS = {"DEV-SITE-01": 1}   # is device ki clock itne ghante aage hai

DRIFT_START = {"DEV-SITE-01": "2026-07-01"}

p = pd.read_sql("SELECT punch_id, device_id, device_user_id, punch_time FROM raw_biometric_punches", con)
dm = pd.read_sql("SELECT device_id, device_user_id, emp_id FROM raw_device_mapping", con)
raw_count = len(p)

for df in (p, dm):
    for c in df.columns:
        df[c] = df[c].str.strip()

p["punch_time_raw"] = p["punch_time"]
p["t"] = pd.to_datetime(p["punch_time"])

# 1. Diagnosis: har device/month mein hour 5,6,7 ka share
d = p[p["t"].dt.hour.isin([5, 6, 7])]
print(pd.crosstab([d["device_id"], d["t"].dt.to_period("M")], d["t"].dt.hour, normalize="index").round(2))

# 2. Clock correction
p["clock_corrected"] = 0
for dev, hrs in CLOCK_OFFSET_HOURS.items():
    m = (p["device_id"] == dev) & (p["t"] >= pd.Timestamp(DRIFT_START[dev]))
    p.loc[m, "t"] = p.loc[m, "t"] - pd.Timedelta(hours=hrs)
    p.loc[m, "clock_corrected"] = 1
    print(dev, "corrected rows:", m.sum())

# 3. Device user -> employee mapping
p = p.merge(dm, on=["device_id", "device_user_id"], how="left")
unmapped = p[p["emp_id"].isna()].copy()
mapped = p[p["emp_id"].notna()].copy()
print("unmapped:", len(unmapped), "| unique unmapped ids:", unmapped["device_user_id"].nunique())

# 4. Duplicate punches (2 minute rule): pichle punch se <= 120 sec
mapped = mapped.sort_values(["emp_id", "t"]).reset_index(drop=True)
gap = mapped.groupby("emp_id")["t"].diff().dt.total_seconds()
is_dup = gap <= 120
dups = mapped[is_dup].copy()
clean = mapped[~is_dup].copy()
print("duplicates removed:", len(dups))

# 5. Rejected table
unmapped["reason"] = "unmapped device_user_id (no employee mapping)"
dups["reason"] = "duplicate punch within 2 minutes of previous punch"
cols = ["punch_id", "device_id", "device_user_id", "punch_time_raw", "reason"]
rejected = pd.concat([unmapped[cols], dups[cols]])

# 6. Staging
clean["punch_time"] = clean["t"].dt.strftime("%Y-%m-%d %H:%M:%S")
stg = clean[["punch_id", "device_id", "emp_id", "punch_time", "punch_time_raw", "clock_corrected"]]
stg.to_sql("stg_punches", con, if_exists="replace", index=False)
rejected.to_sql("stg_rejected_punches", con, if_exists="replace", index=False)

# 7. Reconcile + sanity
print("raw:", raw_count, "| staging:", len(stg), "| rejected:", len(rejected))
print("reconcile OK:", raw_count == len(stg) + len(rejected))
emp = pd.read_sql("SELECT emp_id FROM stg_employees", con)
print("mapped emp_id not in employees:", (~stg["emp_id"].isin(emp["emp_id"])).sum())
con.commit()

DRIFT_START = {"DEV-SITE-01": "2026-07-01"}   # date yahan badal lena


m = (p["device_id"] == dev) & (p["t"] >= pd.Timestamp(DRIFT_START[dev]))