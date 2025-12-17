import pandas as pd
import glob
import os

processed_dir = r"c:\Users\mianm\Work\CalYMayor1\kido-ruteo\data\processed"
files = glob.glob(os.path.join(processed_dir, "processed_checkpoint*.csv"))

print(f"Checking {len(files)} files...")

for f in files:
    df = pd.read_csv(f)
    # Check for non-null veh_total
    valid_rows = df[df['veh_total'].notna()]
    if not valid_rows.empty:
        print(f"\nFile: {os.path.basename(f)}")
        print(valid_rows.head(1).to_string())
        break
else:
    print("No non-null veh_total found in any file.")
