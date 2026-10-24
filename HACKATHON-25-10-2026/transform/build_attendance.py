import pandas as pd, numpy as np, sqlite3
con = sqlite3.connect("hr.db")

PLANT_CODE = {"Head Office": "HO", "Korangi Plant": "KOR", "SITE Plant": "SITE", "Faisalabad Plant": "FSD"}
START_H = {"DAY": 6, "EVE": 14, "NIGHT": 22, "GEN": 9}
END_H = {"DAY": 14, "EVE": 22, "NIGHT": 30, "GEN": 17.5}   # NIGHT 30 = agle din 06:00

sch = pd.read_sql("SELECT emp_id, plant, work_date, shift_code FROM stg_schedule", con)
sch["work_date"] = pd.to_datetime(sch["work_date"])

# 1. Punches ko shift ki start date par lagao (rule 7)
p = pd.read_sql("SELECT emp_id, punch_time FROM stg_punches", con)
p["t"] = pd.to_datetime(p["punch_time"])
p["cal_date"] = p["t"].dt.normalize()
p["prev_date"] = p["cal_date"] - pd.Timedelta(days=1)
prev = sch[["emp_id", "work_date", "shift_code"]].rename(columns={"work_date": "prev_date", "shift_code": "prev_shift"})
p = p.merge(prev, on=["emp_id", "prev_date"], how="left")
night_tail = (p["prev_shift"] == "NIGHT") & (p["t"].dt.hour < 12)
p["work_date"] = np.where(night_tail, p["prev_date"], p["cal_date"])
print("night punches moved to previous date:", int(night_tail.sum()))

# 2. Pehla aur aakhri punch (rule 10)
g = (p.groupby(["emp_id", "work_date"])["t"]
       .agg(check_in="min", check_out="max", punch_count="count").reset_index())
a = sch.merge(g, on=["emp_id", "work_date"], how="left")
a["punch_count"] = a["punch_count"].fillna(0).astype(int)
orphans = len(g) - a[a["punch_count"] > 0].shape[0]
print("punch-days outside employee schedule (ignored):", orphans)

# 3. Sunday, holiday, leave
a["is_sunday"] = (a["work_date"].dt.weekday == 6).astype(int)
a["plant_code"] = a["plant"].map(PLANT_CODE)
hol = pd.read_sql("SELECT holiday_date, scope FROM raw_holidays", con)
hol["holiday_date"] = pd.to_datetime(hol["holiday_date"].str.strip())
hol["scope"] = hol["scope"].str.strip().str.upper()
all_h = set(hol.loc[hol["scope"] == "ALL", "holiday_date"])
pl = hol[hol["scope"] != "ALL"].assign(plant_hol=1)
a = a.merge(pl[["holiday_date", "scope", "plant_hol"]], left_on=["work_date", "plant_code"],
            right_on=["holiday_date", "scope"], how="left")
a["is_holiday"] = (a["work_date"].isin(all_h) | a["plant_hol"].notna()).astype(int)

ld = pd.read_sql("SELECT DISTINCT emp_id, leave_date FROM stg_leave_days", con)
ld["leave_date"] = pd.to_datetime(ld["leave_date"])
ld["on_leave"] = 1
a = a.merge(ld, left_on=["emp_id", "work_date"], right_on=["emp_id", "leave_date"], how="left")
a["on_leave"] = a["on_leave"].fillna(0).astype(int)

# 4. Status (rule 12, isi order mein)
a["status"] = np.select(
    [(a["is_sunday"] == 1) & (a["punch_count"] == 0),
     (a["is_holiday"] == 1) & (a["punch_count"] == 0),
     a["on_leave"] == 1,
     a["punch_count"] >= 2,
     a["punch_count"] == 1],
    ["Weekly Off", "Holiday", "On Leave", "Present", "Missing Punch"], default="Absent")

# 5. Hours, late, early, overtime
a["shift_start"] = a["work_date"] + pd.to_timedelta(a["shift_code"].map(START_H), unit="h")
a["shift_end"] = a["work_date"] + pd.to_timedelta(a["shift_code"].map(END_H), unit="h")
present = a["status"] == "Present"
working = (a["is_sunday"] == 0) & (a["is_holiday"] == 0)

a["worked_minutes"] = np.where(a["punch_count"] >= 2, (a["check_out"] - a["check_in"]).dt.total_seconds() / 60, 0)
a["worked_hours"] = (a["worked_minutes"] / 60).round(2)

late = (a["check_in"] - a["shift_start"]).dt.total_seconds() / 60
early = (a["shift_end"] - a["check_out"]).dt.total_seconds() / 60
a["late_minutes"] = np.where(present & working & (late > 10), late.round(1), 0)
a["early_departure_minutes"] = np.where(present & working & (early > 10), early.round(1), 0)

after_end = ((a["check_out"] - a["shift_end"]).dt.total_seconds() / 60).clip(lower=0)
ot_minutes = np.where(working, after_end, a["worked_minutes"])
a["overtime_hours"] = np.where(present, np.floor(ot_minutes / 30) * 0.5, 0)

# 6. Save
out = a[["emp_id", "plant", "work_date", "shift_code", "check_in", "check_out", "punch_count", "worked_hours",
         "late_minutes", "early_departure_minutes", "overtime_hours", "is_sunday", "is_holiday", "status"]].copy()
for c in ["work_date", "check_in", "check_out"]:
    out[c] = out[c].dt.strftime("%Y-%m-%d" if c == "work_date" else "%Y-%m-%d %H:%M:%S")
out.to_sql("stg_attendance_daily", con, if_exists="replace", index=False)

print("schedule rows:", len(sch), "| attendance rows:", len(out), "| match:", len(sch) == len(out))
print(out["status"].value_counts().to_dict())
print("negative worked hours:", (out["worked_hours"] < 0).sum(), "| shifts > 16h:", (out["worked_hours"] > 16).sum())
print("late days:", (out["late_minutes"] > 0).sum(), "| total OT hours:", out["overtime_hours"].sum())
print(out.assign(m=out["work_date"].str[:7]).groupby("m")["overtime_hours"].sum().to_dict())
con.commit()