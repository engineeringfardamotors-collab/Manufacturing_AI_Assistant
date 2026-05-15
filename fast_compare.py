import pandas as pd
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, '.')

packing_file = 'data/uploads/20260511_235202_OM25094_120_T5_Plus1_CKD_Loading_list.xlsx'
balance_file = 'data/uploads/20260511_230701_EBS-T5Plus-002_Balance_7_JPH_V2.xlsx'
SHIPMENT_UNITS = 120

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

# Packing
xls_p = pd.ExcelFile(packing_file)
raw_p = pd.read_excel(packing_file, sheet_name=xls_p.sheet_names[1])
df_p_raw = pd.DataFrame({
    "part_number": raw_p.iloc[:, 5].apply(clean_part_number),
    "quantity": pd.to_numeric(raw_p.iloc[:, 8], errors="coerce").fillna(0)
})
df_p_raw = df_p_raw[df_p_raw["part_number"] != ""].copy()
agg = df_p_raw.groupby("part_number", as_index=False)["quantity"].sum()
agg["quantity"] = agg["quantity"] / SHIPMENT_UNITS
left_parts = set(agg["part_number"].tolist())

# Balance
xls_b = pd.ExcelFile(balance_file)
target_sheet = next((sh for sh in xls_b.sheet_names if sh.strip() == "اصلی"), xls_b.sheet_names[0])
raw_b = pd.read_excel(balance_file, sheet_name=target_sheet, header=1)
right_df = pd.DataFrame({
    "part_number": raw_b.iloc[:, 7].apply(clean_balance_part),
    "alternative_part": raw_b.iloc[:, 8].apply(clean_balance_part),
    "quantity": pd.to_numeric(raw_b.iloc[:, 10], errors="coerce").fillna(0),
})
right_df = right_df[right_df["part_number"] != ""].copy()
right_parts = set(right_df["part_number"].tolist())

# --- Fast comparison ---
exact_matches = left_parts & right_parts
missing = left_parts - right_parts
extra = right_parts - left_parts

# Suffix check برای missing
import re
SUFFIX_PAT = re.compile(r"^(.+)-L\d{2}$", re.IGNORECASE)

suffix_matched = set()
suffix_pairs = []
for lp in list(missing):
    m = SUFFIX_PAT.match(lp)
    base = m.group(1) if m else None
    # آیا base در right هست؟
    if base and base in right_parts:
        suffix_matched.add(lp)
        suffix_pairs.append((lp, base, "suffix_L"))
        continue
    # آیا یک right part با این base وجود دارد؟
    for rp in right_parts:
        rm = SUFFIX_PAT.match(rp)
        rbase = rm.group(1) if rm else None
        if base and rbase and base == rbase:
            suffix_matched.add(lp)
            suffix_pairs.append((lp, rp, "suffix_base_match"))
            break
        if rbase and rbase == lp:
            suffix_matched.add(lp)
            suffix_pairs.append((lp, rp, "suffix_rp"))
            break

# Alternative check
alt_map = right_df.groupby("part_number")["alternative_part"].apply(set).to_dict()
alt_matched = set()
alt_pairs = []
still_missing = missing - suffix_matched
for lp in still_missing:
    found = False
    for rp, alts in alt_map.items():
        if lp in alts:
            alt_matched.add(lp)
            alt_pairs.append((lp, rp, "alternative"))
            found = True
            break
    if not found:
        # آیا alternative قطعه چپ در right هست؟
        pass

final_missing = still_missing - alt_matched

print("=== FAST COMPARISON RESULTS ===")
print(f"Left parts:          {len(left_parts)}")
print(f"Right parts:         {len(right_parts)}")
print(f"Exact matches:       {len(exact_matches)}")
print(f"Suffix matches:      {len(suffix_matched)}")
print(f"Alternative matches: {len(alt_matched)}")
print(f"Total matched:       {len(exact_matches) + len(suffix_matched) + len(alt_matched)}")
print(f"Missing in right:    {len(final_missing)}")
print(f"Extra in right:      {len(extra)}")
if final_missing:
    print("\nSample missing:", list(final_missing)[:10])
if suffix_pairs:
    print("\nSample suffix pairs:", suffix_pairs[:5])

sys.stdout.flush()
