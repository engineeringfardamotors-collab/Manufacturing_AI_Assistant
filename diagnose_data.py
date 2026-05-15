import pandas as pd
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

packing_file = 'data/uploads/20260511_235202_OM25094_120_T5_Plus1_CKD_Loading_list.xlsx'
balance_file = 'data/uploads/20260511_230701_EBS-T5Plus-002_Balance_7_JPH_V2.xlsx'

# --- پاکسازی ---
def clean_part_number(x) -> str:
    s = "" if pd.isna(x) else str(x).strip()
    if s in ("", ".", "..", "...", "....", "-", "—"):
        return ""
    return s

def clean_balance_part(x) -> str:
    s = "" if pd.isna(x) else str(x).strip().strip("'").strip()
    if s in ("", ".", "..", "...", "....", "-", "—", "…"):
        return ""
    return s

# --- پکینگ ---
xls_p = pd.ExcelFile(packing_file)
raw_p = pd.read_excel(packing_file, sheet_name=xls_p.sheet_names[1])
p_parts = set(
    clean_part_number(x) for x in raw_p.iloc[:, 5]
    if clean_part_number(x) != ""
)

# --- بالانس ---
xls_b = pd.ExcelFile(balance_file)
target_sheet = next((sh for sh in xls_b.sheet_names if sh.strip() == "اصلی"), xls_b.sheet_names[0])
print(f"Balance sheet used: '{target_sheet}'")
raw_b = pd.read_excel(balance_file, sheet_name=target_sheet, header=1)
print(f"Balance shape: {raw_b.shape}")
print(f"Balance columns: {list(raw_b.columns[:12])}")
print("--- Col 7 (part_number) first 10 ---")
for i, v in enumerate(raw_b.iloc[:10, 7].tolist()):
    print(f"  [{i}] repr={repr(v)}")

b_parts = set(
    clean_balance_part(x) for x in raw_b.iloc[:, 7]
    if clean_balance_part(x) != ""
)

print(f"\nPacking unique parts: {len(p_parts)}")
print(f"Balance unique parts: {len(b_parts)}")
overlap = p_parts & b_parts
print(f"Direct overlap (exact match): {len(overlap)}")
if overlap:
    print("Sample overlap:", list(overlap)[:10])
else:
    print("Still NO overlap!")
    print("Sample packing:", list(p_parts)[:5])
    print("Sample balance:", list(b_parts)[:5])

sys.stdout.flush()
