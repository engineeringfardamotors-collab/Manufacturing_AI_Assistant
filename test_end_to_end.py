import pandas as pd
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, '.')

from services.engine.comparator import DatasetComparator

packing_file = 'data/uploads/20260511_235202_OM25094_120_T5_Plus1_CKD_Loading_list.xlsx'
balance_file = 'data/uploads/20260511_230701_EBS-T5Plus-002_Balance_7_JPH_V2.xlsx'
SHIPMENT_UNITS = 120

# --- پکینگ reader ---
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
    "alternative_part": "",
    "quantity": pd.to_numeric(raw_p.iloc[:, 8], errors="coerce").fillna(0)
})
df_p_raw = df_p_raw[df_p_raw["part_number"] != ""].copy()
agg = df_p_raw.groupby("part_number", as_index=False)["quantity"].sum().rename(columns={"quantity": "packing_qty_total"})
agg["quantity"] = agg["packing_qty_total"] / SHIPMENT_UNITS
agg["alternative_part"] = ""
agg["description"] = ""
left_df = agg[["part_number", "alternative_part", "quantity", "description"]].copy()

# Balance
xls_b = pd.ExcelFile(balance_file)
target_sheet = next((sh for sh in xls_b.sheet_names if sh.strip() == "اصلی"), xls_b.sheet_names[0])
raw_b = pd.read_excel(balance_file, sheet_name=target_sheet, header=1)
right_df = pd.DataFrame({
    "part_number": raw_b.iloc[:, 7].apply(clean_balance_part),
    "alternative_part": raw_b.iloc[:, 8].apply(clean_balance_part),
    "quantity": pd.to_numeric(raw_b.iloc[:, 10], errors="coerce").fillna(0),
    "description": ""
})
right_df = right_df[right_df["part_number"] != ""].copy()

print(f"Left (Packing) rows: {len(left_df)}, unique parts: {left_df['part_number'].nunique()}")
print(f"Right (Balance) rows: {len(right_df)}, unique parts: {right_df['part_number'].nunique()}")

# Compare
comparator = DatasetComparator()
result = comparator.compare(left_df, right_df)

kpi = result["kpi_cards"]
print("\n=== KPI RESULTS ===")
print(f"Total Matched   : {kpi['total_matched']}")
print(f"  - Exact       : {kpi['exact_count']} ({kpi['exact_pct']}%)")
print(f"  - Alternative : {kpi['alternative_count']} ({kpi['alternative_pct']}%)")
print(f"  - Suffix      : {kpi['suffix_count']} ({kpi['suffix_pct']}%)")
print(f"Qty Mismatches  : {kpi['qty_mismatches']}")
print(f"Missing in Right: {kpi['missing_in_right']}")
print(f"Extra in Right  : {kpi['extra_in_right']}")
print(f"Qty Match Rate  : {kpi['qty_match_rate_pct']}%")

if result["missing_in_right"]:
    print("\nSample Missing in Right:", result["missing_in_right"][:10])

sys.stdout.flush()
