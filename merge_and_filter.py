from pathlib import Path
import pandas as pd

# Folder containing the CSVs (current folder)
folder = Path("./transactions")

# Adjust if your files have a consistent pattern, e.g. "transactions_*.csv"
csv_files = sorted(folder.glob("*.csv"))

if not csv_files:
    raise SystemExit("No CSV files found in the current folder.")

frames = []
for f in csv_files:
    # dtype=str prevents pandas guessing types differently between files
    df = pd.read_csv(f, dtype=str, keep_default_na=False)
    df["__source_file"] = f.name  # optional: helps trace where a row came from
    frames.append(df)

merged = pd.concat(frames, ignore_index=True)

# Remove rows where ANY column contains "FEE INCLUDED" (case-insensitive)
mask_fee = merged.astype(str).apply(
    lambda col: col.str.contains("FEES INCLUDED", case=False, na=False)
).any(axis=1)

filtered = merged.loc[~mask_fee].copy()

out_path = folder / "merged_filtered_transactions.csv"
filtered.to_csv(out_path, index=False)

print(f"Merged {len(csv_files)} files")
print(f"Rows before: {len(merged)}")
print(f"Rows removed (FEE INCLUDED): {int(mask_fee.sum())}")
print(f"Rows after: {len(filtered)}")
print(f"Saved: {out_path}")
