"""
update_data.py
──────────────
Run this script on your computer whenever you have new weekly files to add.
It merges all your .xlsx files into one data/sales_data.parquet file,
which you then upload to GitHub — the app loads it automatically.

Usage:
  1. Put your weekly .xlsx files inside the  weekly_files/  folder
  2. Open a terminal in this folder and run:
         python update_data.py
  3. Upload the updated  data/sales_data.parquet  to GitHub
  4. The app redeploys automatically — everyone sees the new data

You can run this as many times as you want.
Duplicate weeks are handled automatically.
"""

import os
import sys
import pandas as pd
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────
INPUT_FOLDER  = Path("weekly_files")   # drop your .xlsx files here
OUTPUT_FOLDER = Path("data")
OUTPUT_FILE   = OUTPUT_FOLDER / "sales_data.parquet"

# ── Column detection (same logic as app.py) ───────────────────────────────────
def find_column(df, candidates):
    col_lower = {c.lower().strip(): c for c in df.columns}
    for cand in candidates:
        if cand.lower() in col_lower:
            return col_lower[cand.lower()]
    return None


def parse_xlsx(filepath: Path) -> pd.DataFrame:
    try:
        df = pd.read_excel(filepath, sheet_name="Transactions", engine="openpyxl")
    except Exception:
        df = pd.read_excel(filepath, sheet_name=0, engine="openpyxl")

    df.columns = df.columns.str.strip()

    date_col = find_column(df, ["date", "transaction date", "sale date", "trans date"])
    item_col = find_column(df, ["product name", "item", "item name", "product",
                                "description", "desc", "name", "menu item"])
    qty_col  = find_column(df, ["qs", "qty", "quantity", "units", "count",
                                "sold", "units sold"])
    rev_col  = find_column(df, ["qs*rcp", "total", "revenue", "sales", "price",
                                "amount", "gross", "net sales", "ext price",
                                "extended price", "total price"])

    if not date_col or not item_col:
        print(f"  ⚠️  Skipping {filepath.name} — could not find date or item columns")
        return pd.DataFrame()
    if not qty_col and not rev_col:
        print(f"  ⚠️  Skipping {filepath.name} — could not find quantity or revenue columns")
        return pd.DataFrame()

    clean = pd.DataFrame()
    clean["date"] = pd.to_datetime(df[date_col], errors="coerce").dt.normalize()
    clean["item"] = df[item_col].astype(str).str.strip()
    clean["qty"]  = pd.to_numeric(df[qty_col], errors="coerce").fillna(0) if qty_col else 0.0
    clean["rev"]  = pd.to_numeric(df[rev_col], errors="coerce").fillna(0) if rev_col else 0.0

    clean = clean.dropna(subset=["date"])
    clean = clean[clean["item"].str.len() > 0]
    clean = clean[clean["item"] != "nan"]
    return clean


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print("=" * 55)
    print("  SnowFruit Data Updater")
    print("=" * 55)

    # Make sure folders exist
    INPUT_FOLDER.mkdir(exist_ok=True)
    OUTPUT_FOLDER.mkdir(exist_ok=True)

    # Find xlsx files
    xlsx_files = sorted(INPUT_FOLDER.glob("*.xlsx"))
    if not xlsx_files:
        print(f"\n❌  No .xlsx files found in '{INPUT_FOLDER}/'")
        print(f"   Put your weekly files there and run this script again.")
        sys.exit(1)

    print(f"\n📂  Found {len(xlsx_files)} file(s) in '{INPUT_FOLDER}/':")
    for f in xlsx_files:
        print(f"     • {f.name}")

    # Parse each file
    print("\n⏳  Parsing files…")
    frames = []
    for f in xlsx_files:
        print(f"  → {f.name}", end=" ")
        parsed = parse_xlsx(f)
        if parsed.empty:
            continue
        frames.append(parsed)
        rows = len(parsed)
        date_range = f"{parsed['date'].min().strftime('%b %d')}–{parsed['date'].max().strftime('%b %d, %Y')}"
        print(f"✅  {rows} rows  |  {date_range}")

    if not frames:
        print("\n❌  No valid data parsed from any file. Check your column names.")
        sys.exit(1)

    new_data = pd.concat(frames, ignore_index=True)

    # Load existing parquet and merge
    if OUTPUT_FILE.exists():
        print(f"\n📦  Loading existing data from {OUTPUT_FILE}…")
        existing = pd.read_parquet(OUTPUT_FILE)
        before = len(existing)
        combined = pd.concat([existing, new_data], ignore_index=True).drop_duplicates()
        added = len(combined) - before
        print(f"     Existing rows : {before:,}")
        print(f"     New rows added: {added:,}")
        print(f"     Total rows    : {len(combined):,}")
    else:
        print(f"\n🆕  No existing data found — creating fresh dataset.")
        combined = new_data.drop_duplicates()
        print(f"     Total rows: {len(combined):,}")

    # Save
    combined.to_parquet(OUTPUT_FILE, index=False)
    print(f"\n✅  Saved → {OUTPUT_FILE}")

    # Summary
    print("\n" + "=" * 55)
    print("  Summary")
    print("=" * 55)
    print(f"  Date range  : {combined['date'].min().strftime('%b %d')} – {combined['date'].max().strftime('%b %d, %Y')}")
    print(f"  Total units : {int(combined['qty'].sum()):,}")
    print(f"  Total rev   : ${combined['rev'].sum():,.2f}")
    print(f"  Unique items: {combined['item'].nunique()}")

    monthly = combined.copy()
    monthly["month"] = monthly["date"].dt.strftime("%b %Y")
    monthly_agg = monthly.groupby("month")["rev"].sum().sort_values(ascending=False)
    print(f"\n  Revenue by month:")
    for month, rev in monthly_agg.items():
        print(f"     {month:<12} ${rev:,.2f}")

    print("\n" + "=" * 55)
    print("  NEXT STEP:")
    print("  Upload  data/sales_data.parquet  to your GitHub repo.")
    print("  The app will redeploy and everyone sees the new data.")
    print("=" * 55)


if __name__ == "__main__":
    main()
