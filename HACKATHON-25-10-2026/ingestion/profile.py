import pandas as pd, sqlite3
con = sqlite3.connect("hr.db")

df = pd.read_sql("SELECT * FROM raw_employees", con)
print(df.columns.tolist())
print(df.head(5).to_string())
print("\nNulls:\n", df.isna().sum())
print("\nDuplicate emp_id:", df["emp_id"].duplicated().sum())

for col in df.columns:
    if "date" in col.lower() or col.lower() in ("dob", "doj"):
        print(f"\n{col} samples:", df[col].dropna().sample(8, random_state=1).tolist())

for col in df.columns:
    if "dept" in col.lower() or "department" in col.lower():
        print(f"\n{col} unique:\n", df[col].value_counts().head(30))