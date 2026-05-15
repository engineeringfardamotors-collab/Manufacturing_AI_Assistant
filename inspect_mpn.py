import pandas as pd
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

mpn_file = 'data/uploads/EXPORT_MPN.xlsx'

print("=== EXPORT_MPN FILE INSPECTION ===")
xls = pd.ExcelFile(mpn_file)
print("Sheets:", xls.sheet_names)

for sh in xls.sheet_names[:3]:
    print(f"\n--- Sheet: '{sh}' ---")
    raw = pd.read_excel(mpn_file, sheet_name=sh, header=None)
    print(f"Shape: {raw.shape}")
    print("First 5 rows:")
    for r in range(min(5, raw.shape[0])):
        row_data = [repr(raw.iloc[r, c]) for c in range(min(12, raw.shape[1]))]
        print(f"  row[{r}]: {row_data}")

# Try with header=0
print("\n=== WITH header=0 (first sheet) ===")
df = pd.read_excel(mpn_file, sheet_name=xls.sheet_names[0], header=0)
print(f"Shape: {df.shape}")
print("Columns:", list(df.columns))
print("First 10 rows:")
print(df.head(10).to_string())

sys.stdout.flush()
