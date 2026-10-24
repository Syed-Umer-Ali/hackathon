import pandas as pd, sqlite3
from datetime import datetime

con = sqlite3.connect("hr.db")
df = pd.read_sql("SELECT * FROM raw_employees", con)
raw_count = len(df)

# 1. Saare text columns trim (aage peeche + beech ke extra spaces)
text_cols = ["emp_id", "full_name", "gender", "date_of_birth", "email", "phone", "plant",
             "department", "designation", "grade", "employment_type", "hire_date",
             "separation_date", "status", "annual_leave_entitlement", "updated_at"]
for c in text_cols:
    df[c] = df[c].astype(str).str.strip().str.replace(r"\s+", " ", regex=True)
    df[c] = df[c].replace("", None)

# 2. Casing
df["department"] = df["department"].str.title().replace({"It": "IT"})
df["gender"] = df["gender"].str.upper()
df["email"] = df["email"].str.lower()

# 3. Dates -> ISO YYYY-MM-DD
def to_iso(s):
    if s is None or pd.isna(s):
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%b-%Y"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return "UNPARSED:" + s

for c in ["date_of_birth", "hire_date", "separation_date"]:
    df[c] = df[c].apply(to_iso)
    print(c, "unparsed:", df[c].astype(str).str.startswith("UNPARSED").sum())

df["updated_at"] = pd.to_datetime(df["updated_at"])
df["annual_leave_entitlement"] = pd.to_numeric(df["annual_leave_entitlement"])

# 4. Dedupe: latest updated_at rakho, baqi merge_log mein
df = df.sort_values(["emp_id", "updated_at"], ascending=[True, False])
df["rn"] = df.groupby("emp_id").cumcount()
kept = df[df["rn"] == 0].set_index("emp_id")
dropped = df[df["rn"] > 0].copy()

log = pd.DataFrame({
    "emp_id": dropped["emp_id"],
    "dropped_row_hash": dropped["_row_hash"],
    "dropped_updated_at": dropped["updated_at"].astype(str),
    "kept_row_hash": dropped["emp_id"].map(kept["_row_hash"]),
    "kept_updated_at": dropped["emp_id"].map(kept["updated_at"]).astype(str),
    "reason": "duplicate emp_id; kept row with latest updated_at",
})

clean = df[df["rn"] == 0].drop(columns=["rn"])
clean["updated_at"] = clean["updated_at"].astype(str)

# 5. Staging mein likho (replace = dobara chalane pe duplicate nahi)
clean.to_sql("stg_employees", con, if_exists="replace", index=False)
log.to_sql("stg_employee_merge_log", con, if_exists="replace", index=False)

print("raw:", raw_count, "| staging:", len(clean), "| merged away:", len(log))
print("reconcile OK:", raw_count == len(clean) + len(log))
print(pd.read_sql("SELECT department, COUNT(*) n FROM stg_employees GROUP BY 1 ORDER BY 2 DESC", con))
con.commit()


