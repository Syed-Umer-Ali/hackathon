import sqlite3, glob, os
import pandas as pd

con = sqlite3.connect("hr.db")
con.executescript(open("analytics/00_helpers.sql", encoding="utf-8").read())
os.makedirs("analytics/results", exist_ok=True)

for f in sorted(glob.glob("analytics/q*.sql")):
    name = os.path.splitext(os.path.basename(f))[0]
    df = pd.read_sql(open(f, encoding="utf-8").read(), con)
    df.to_csv(f"analytics/results/{name}.csv", index=False)
    print(f"{name}: {len(df)} rows")
    if name[:3] in ("q06", "q07", "q08"):
        print(df.head(8).to_string(index=False), "\n")
con.close()