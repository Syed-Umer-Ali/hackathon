import pandas as pd, sqlite3
con = sqlite3.connect("hr.db")
START, END = pd.Timestamp("2026-04-01"), pd.Timestamp("2026-09-30")

# 1. Roster saaf karo
r = pd.read_sql("SELECT emp_id, week_start, shift_code FROM raw_shift_roster", con)
for c in r.columns:
    r[c] = r[c].str.strip()
r["shift_code"] = r["shift_code"].str.upper()
r["week_start"] = pd.to_datetime(r["week_start"])
print("roster rows:", len(r), "| dup (emp,week):", r.duplicated(["emp_id", "week_start"]).sum(),
      "| week_start not Monday:", (r["week_start"].dt.weekday != 0).sum(),
      "| shifts:", r["shift_code"].unique().tolist())
r = r.drop_duplicates(["emp_id", "week_start"], keep="last")

# 2. Har employee ke liye saare haftay, missing hafta = pichle hafte wali shift (rule 6)
e = pd.read_sql("SELECT emp_id, plant, hire_date, separation_date FROM stg_employees", con)
weeks = pd.DataFrame({"week_start": pd.date_range("2026-03-30", "2026-09-28", freq="7D")})
grid = e[["emp_id"]].merge(weeks, how="cross")
grid = grid.merge(r, on=["emp_id", "week_start"], how="left")
print("missing roster weeks:", grid["shift_code"].isna().sum())
grid = grid.sort_values(["emp_id", "week_start"])
grid["shift_code"] = grid.groupby("emp_id")["shift_code"].ffill()
print("weeks still without shift (no earlier week):", grid["shift_code"].isna().sum(),
      "| employees:", grid[grid["shift_code"].isna()]["emp_id"].nunique())

# 3. Employment ke har din ki row
days = pd.DataFrame({"work_date": pd.date_range(START, END)})
days["week_start"] = days["work_date"] - pd.to_timedelta(days["work_date"].dt.weekday, unit="D")
e["hire"] = pd.to_datetime(e["hire_date"])
e["sep"] = pd.to_datetime(e["separation_date"])
s = e.merge(days, how="cross")
s = s[(s["work_date"] >= s["hire"]) & (s["sep"].isna() | (s["work_date"] <= s["sep"]))]
s = s.merge(grid, on=["emp_id", "week_start"], how="left")
s = s[["emp_id", "plant", "work_date", "week_start", "shift_code"]]
s["work_date"] = s["work_date"].dt.strftime("%Y-%m-%d")
s["week_start"] = s["week_start"].dt.strftime("%Y-%m-%d")

s.to_sql("stg_schedule", con, if_exists="replace", index=False)
print("schedule rows:", len(s), "| employees:", s["emp_id"].nunique(),
      "| rows without shift:", s["shift_code"].isna().sum())
print(s["shift_code"].value_counts(dropna=False).to_dict())
con.commit()