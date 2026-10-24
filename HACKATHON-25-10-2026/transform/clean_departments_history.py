import pandas as pd, sqlite3
from datetime import datetime

con = sqlite3.connect("hr.db")
META = ["_row_hash", "_source_file", "_loaded_at"]

def to_iso(s):
    if s is None or pd.isna(s) or str(s).strip() == "":
        return None
    s = str(s).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%b-%Y"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return "UNPARSED:" + s

# ---------- 1. departments ----------
d = pd.read_sql("SELECT * FROM raw_departments", con)
for c in ["dept_id", "dept_name", "plant", "cost_center", "previous_name"]:
    d[c] = d[c].str.strip().replace("", None)
d["renamed_on"] = d["renamed_on"].apply(to_iso)
d = d.drop(columns=META)
d.to_sql("stg_departments", con, if_exists="replace", index=False)
print("departments:", len(d))

# check: employees ka (plant, department) dept_id se match hota hai?
e = pd.read_sql("SELECT emp_id, plant, department FROM stg_employees", con)
rename = {r.previous_name: r.dept_name for r in d.itertuples() if r.previous_name}
e["department"] = e["department"].replace(rename)
m = e.merge(d, left_on=["plant", "department"], right_on=["plant", "dept_name"], how="left")
print("employees without dept match:", m["dept_id"].isna().sum())
print(m[m["dept_id"].isna()][["plant", "department"]].drop_duplicates())

# ---------- 2. employment history ----------
h = pd.read_sql("SELECT * FROM raw_employment_history", con)
raw_count = len(h)
for c in ["emp_id", "effective_from", "effective_to", "dept_id", "designation",
          "grade", "basic_salary", "change_reason"]:
    h[c] = h[c].astype(str).str.strip().replace("", None)

for c in ["effective_from", "effective_to"]:
    h[c] = h[c].apply(to_iso)
    print(c, "unparsed:", h[c].astype(str).str.startswith("UNPARSED").sum())

h["basic_salary"] = pd.to_numeric(h["basic_salary"])
h = h.drop(columns=META)

# exact duplicates
dups = h.duplicated(subset=["emp_id", "effective_from"], keep="first")
print("duplicate (emp_id, effective_from):", dups.sum())
h = h[~dups]

# SCD2: valid_to = agle record ki date - 1 din
h = h.sort_values(["emp_id", "effective_from"]).reset_index(drop=True)
nxt = h.groupby("emp_id")["effective_from"].shift(-1)
h["valid_from"] = h["effective_from"]
h["valid_to"] = (pd.to_datetime(nxt) - pd.Timedelta(days=1)).dt.strftime("%Y-%m-%d")
h["is_current"] = h["valid_to"].isna().astype(int)

# effective_to raw se kitni jagah farq hai (planted issue)
diff = h[(h["effective_to"].notna() | h["valid_to"].notna()) &
         (h["effective_to"] != h["valid_to"])]
print("rows where raw effective_to != derived valid_to:", len(diff),
      "| employees:", diff["emp_id"].nunique())

h = h.rename(columns={"effective_to": "effective_to_raw"})
h.to_sql("stg_employment_history", con, if_exists="replace", index=False)

print("raw:", raw_count, "| staging:", len(h), "| removed dups:", dups.sum())
print("reconcile OK:", raw_count == len(h) + dups.sum())
print("employees in history:", h["emp_id"].nunique())
con.commit()