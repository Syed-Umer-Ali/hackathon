import pandas as pd, sqlite3, hashlib, json, os
from datetime import datetime

DATA_DIR = "data"
con = sqlite3.connect("hr.db")

con.execute("""CREATE TABLE IF NOT EXISTS load_log(
    file TEXT, table_name TEXT, file_rows INT, table_rows INT, status TEXT, loaded_at TEXT)""")

def read_file(path):
    if path.endswith(".csv"):
        return pd.read_csv(path, dtype=str, keep_default_na=False)
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        data = next(v for v in data.values() if isinstance(v, list))
    df = pd.DataFrame(data)
    for c in df.columns:
        df[c] = df[c].apply(lambda x: json.dumps(x) if isinstance(x, (list, dict)) else str(x))
    return df

def load(file):
    path = os.path.join(DATA_DIR, file)
    table = "raw_" + os.path.splitext(file)[0]
    df = read_file(path)
    file_rows = len(df)

    df["_row_hash"] = df.apply(
        lambda r: hashlib.md5("|".join(r.astype(str)).encode()).hexdigest(), axis=1)
    df["_source_file"] = file
    df["_loaded_at"] = datetime.now().isoformat(timespec="seconds")

    exists = con.execute("SELECT 1 FROM sqlite_master WHERE name=?", (table,)).fetchone()
    if exists:
        con.execute(f"DELETE FROM {table} WHERE _source_file=?", (file,))
    df.to_sql(table, con, if_exists="append", index=False)

    table_rows = con.execute(
        f"SELECT COUNT(*) FROM {table} WHERE _source_file=?", (file,)).fetchone()[0]
    status = "OK" if file_rows == table_rows else "MISMATCH"
    con.execute("INSERT INTO load_log VALUES (?,?,?,?,?,?)",
                (file, table, file_rows, table_rows, status,
                 datetime.now().isoformat(timespec="seconds")))
    con.commit()
    print(f"{file}: file={file_rows} table={table_rows} {status}")

for f in sorted(os.listdir(DATA_DIR)):
    if f.endswith((".csv", ".json")):
        load(f)