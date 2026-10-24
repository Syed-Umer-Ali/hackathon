import pandas as pd, sqlite3
con = sqlite3.connect("hr.db")
p = pd.read_sql("SELECT punch_time FROM raw_biometric_punches WHERE device_id='DEV-SITE-01'", con)
p["t"] = pd.to_datetime(p["punch_time"])
d = p[p["t"].dt.hour.isin([5, 6, 7])].copy()
d["day"] = d["t"].dt.strftime("%Y-%m-%d")
r = d.groupby("day")["t"].apply(lambda s: (s.dt.hour == 7).mean()).round(2)
print(r.loc["2026-06-25":"2026-07-05"])