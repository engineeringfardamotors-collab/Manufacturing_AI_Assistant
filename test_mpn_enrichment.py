import pandas as pd
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, '.')

from services.engine.comparator import DatasetComparator
from services.engine.mpn_reader import SapMpnReader

# --- Packing List ---
packing_file = 'data/uploads/20260511_235202_OM25094_120_T5_Plus1_CKD_Loading_list.xlsx'
xls_p = pd.ExcelFile(packing_file)
raw_p = pd.read_excel(packing_file, sheet_name=xls_p.sheet_names[1])
left_df = pd.DataFrame({
    "part_number": raw_p.iloc[:, 5].apply(lambda x: str(x).strip() if not pd.isna(x) else ""),
    "quantity": pd.to_numeric(raw_p.iloc[:, 8], errors="coerce").fillna(0),
})
left_df = left_df[left_df["part_number"] != ""].copy()

# --- Balance ---
balance_file = 'data/uploads/20260511_230701_EBS-T5Plus-002_Balance_7_JPH_V2.xlsx'
xls_b = pd.ExcelFile(balance_file)
target_sheet = next((sh for sh in xls_b.sheet_names if sh.strip() == "اصلی"), xls_b.sheet_names[0])
raw_b = pd.read_excel(balance_file, sheet_name=target_sheet, header=1)
right_df = pd.DataFrame({
    "part_number": raw_b.iloc[:, 7].apply(lambda x: str(x).strip().strip("'") if not pd.isna(x) else ""),
    "alternative_part": raw_b.iloc[:, 8].apply(lambda x: str(x).strip().strip("'") if not pd.isna(x) else ""),
    "quantity": pd.to_numeric(raw_b.iloc[:, 10], errors="coerce").fillna(0),
})
right_df = right_df[right_df["part_number"] != ""].copy()

# --- MPN Lookup ---
mpn_file = 'data/uploads/EXPORT_MPN.xlsx'
mpn_reader = SapMpnReader()
mpn_data = mpn_reader.read(mpn_file)
mpn_lookup = mpn_reader.build_lookup(mpn_data)

# --- Compare with MPN Enrichment ---
comparator = DatasetComparator()
result = comparator.compare(
    left_df=left_df,
    right_df=right_df,
    mpn_lookup=mpn_lookup,
)

kpi = result["kpi_cards"]
print("=== KPI RESULTS WITH MPN ENRICHMENT ===")
print(f"Total Matched   : {kpi['total_matched']}")
print(f"  - Exact       : {kpi['exact_count']} ({kpi['exact_pct']}%)")
print(f"  - Alternative : {kpi['alternative_count']} ({kpi['alternative_pct']}%)")
print(f"  - Suffix      : {kpi['suffix_count']} ({kpi['suffix_pct']}%)")
print(f"  - SAP MPN     : {kpi.get('sap_mpn_count', 0)} ({kpi.get('sap_mpn_pct', 0.0)}%)")
print(f"Qty Mismatches  : {kpi['qty_mismatches']}")
print(f"Missing in Right: {kpi['missing_in_right']}")
print(f"Extra in Right  : {kpi['extra_in_right']}")
print(f"Qty Match Rate  : {kpi['qty_match_rate_pct']}%")

if kpi.get('sap_mpn_count', 0):
    print("\nSample SAP MPN Matches:", result["matched_pairs"][:5])

sys.stdout.flush()
