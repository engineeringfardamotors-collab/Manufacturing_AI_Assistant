import sys
from pathlib import Path

import pandas as pd
import streamlit as st

# --- Path Setup ---
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.engine.comparator import DatasetComparator
from services.engine.database_manager import DatabaseManager

# Initialize Database
db = DatabaseManager()

def clean_part_number(x) -> str:
    s = "" if pd.isna(x) else str(x).strip()
    if s in ("", ".", "..", "...", "....", "-", "—"):
        return ""
    return s

def read_packing_and_aggregate(file, shipment_units: int, product_name: str, db_manager: DatabaseManager) -> pd.DataFrame:
    """
    Reads packing, extracts OM number from filename, 
    aggregates for current view, AND saves to DB for history.
    """
    xls = pd.ExcelFile(file)
    if len(xls.sheet_names) < 2:
        raise ValueError("فایل پکینگ لیست شیت دوم ندارد.")

    # --- Extract OM Number from filename ---
    # Example filename: "OM25094 120 T5 Plus1 CKD Loading list.xlsx"
    file_name_str = file.name
    om_number = file_name_str.split(' ')[0] 
    
    sheet_name = xls.sheet_names[1]
    raw = pd.read_excel(file, sheet_name=sheet_name)

    if raw.shape[1] < 9:
        raise ValueError("ستون‌های اصلی در شیت دوم یافت نشدند.")

    # Extraction
    df = pd.DataFrame({
        "part_number": raw.iloc[:, 5].apply(clean_part_number),
        "alternative_part": "",
        "quantity": pd.to_numeric(raw.iloc[:, 8], errors="coerce").fillna(0)
    })
    
    # Prepare for DB saving
    df_to_save = df[df["part_number"] != ""].copy()
    
    # Save to Database with OM Number
    db_manager.save_packing_data(df_to_save, product_name, om_number, file_name_str)

    # Aggregate for Current View (Current Shipment Only)
    agg = (
        df_to_save.groupby("part_number", as_index=False)["quantity"]
        .sum()
        .rename(columns={"quantity": "packing_qty_total"})
    )
    
    agg["quantity"] = agg["packing_qty_total"] / shipment_units
    agg["alternative_part"] = ""
    agg["description"] = ""
    agg["om_number"] = om_number
    
    return agg[["part_number", "alternative_part", "quantity", "description", "om_number"]].copy()

def read_balance_fixed_format(file) -> pd.DataFrame:
    xls = pd.ExcelFile(file)
    # شیت صحیح: 'اصلی' یا اولین شیتی که این نام را دارد
    target_sheet = None
    for sh in xls.sheet_names:
        if sh.strip() == "اصلی":
            target_sheet = sh
            break
    if target_sheet is None:
        target_sheet = xls.sheet_names[0]

    # header در ردیف دوم (index 1)
    raw = pd.read_excel(file, sheet_name=target_sheet, header=1)

    if raw.shape[1] < 11:
        raise ValueError("فایل بالانس: ستون‌های کافی پیدا نشدند.")

    # پاکسازی مقادیر quoted (مثل "'SX7H-5824020'")
    def clean_balance_part(x) -> str:
        s = "" if pd.isna(x) else str(x).strip().strip("'").strip()
        if s in ("", ".", "..", "...", "....", "-", "—", "…"):
            return ""
        return s

    mapped = pd.DataFrame({
        "part_number": raw.iloc[:, 7].apply(clean_balance_part),
        "alternative_part": raw.iloc[:, 8].apply(clean_balance_part),
        "quantity": pd.to_numeric(raw.iloc[:, 10], errors="coerce").fillna(0),
        "description": ""
    })
    mapped = mapped[mapped["part_number"] != ""].copy()
    return mapped

def show_kpis(kpi: dict):
    st.subheader("KPI Cards")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Matched", kpi.get("total_matched", 0))
    c2.metric("Qty Mismatches", kpi.get("qty_mismatches", 0))
    c3.metric("Missing in Right", kpi.get("missing_in_right", 0))
    c4.metric("Extra in Right", kpi.get("extra_in_right", 0))

# --- UI SETUP ---
st.set_page_config(page_title="Manufacturing AI Assistant", layout="wide")
st.title("Manufacturing AI Assistant")

# 1. Product Selection Section
st.sidebar.header("Product Configuration")
all_products = db.get_all_products()

if all_products.empty:
    st.sidebar.warning("No products in database. Please add one below.")
    new_name = st.sidebar.text_input("New Product Name")
    new_partner = st.sidebar.selectbox("Partner", ["DONGFENG", "CHANGAN", "MG"])
    new_units = st.sidebar.number_input("Shipment Units", value=120)
    if st.sidebar.button("Add Product"):
        db.add_product(new_name, new_partner, new_units)
        st.sidebar.success(f"Added {new_name}")
        st.rerun()
    selected_product = None
else:
    prod_list = all_products['product_name'].tolist()
    selected_product = st.sidebar.selectbox("Select Product", prod_list)
    
    item = all_products[all_products['product_name'] == selected_product].iloc[0]
    st.sidebar.info(f"Partner: {item['partner']}\nUnits: {item['shipment_units']}")
    
    with st.sidebar.expander("Add New Product"):
        n_name = st.text_input("Name")
        n_part = st.selectbox("Partner", ["DONGFENG", "CHANGAN", "MG"])
        n_unit = st.number_input("Units", value=120)
        if st.button("Register"):
            db.add_product(n_name, n_part, n_unit)
            st.rerun()

if selected_product:
    current_prod_info = all_products[all_products['product_name'] == selected_product].iloc[0]
    shipment_units = int(current_prod_info['shipment_units'])
    
    st.header(f"Dashboard: {selected_product}")
    
    # 2. Upload Section
    col_l, col_r, col_mpn, col_bom = st.columns(4)
    with col_l:
        left_file = st.file_uploader("Upload LEFT (Packing List)", type=["xlsx", "xls"], key="left")
    with col_r:
        right_file = st.file_uploader("Upload RIGHT (Balance)", type=["xlsx", "xls"], key="right")
    with col_mpn:
        mpn_file = st.file_uploader("Optional: Upload SAP MPN File", type=["xlsx", "xls"])
    with col_bom:
        bom_file = st.file_uploader("Optional: Upload SAP BOM File (placeholder for later)", type=["xlsx", "xls"])

    if left_file and right_file:
        try:
            # Read & Save to DB & Aggregate
            left_df = read_packing_and_aggregate(left_file, shipment_units, selected_product, db)
            right_df = read_balance_fixed_format(right_file)

            # Process MPN File if provided
            if mpn_file is not None:
                with st.spinner("در حال پردازش فایل SAP MPN..."):
                    mpn_reader = SapMpnReader()
                    mpn_data = mpn_reader.read(mpn_file)
                    mpn_lookup = mpn_reader.build_lookup(mpn_data)
                    st.session_state.mpn_lookup = mpn_lookup
                    st.success("فایل SAP MPN با موفقیت خوانده شد.")
            else:
                mpn_lookup = st.session_state.get("mpn_lookup", None)

            # Placeholder for BOM File processing (for future use)
            if bom_file is not None:
                with st.spinner("در حال پردازش فایل SAP BOM..."):
                    # TODO: Implement BOM file processing
                    st.success("فایل SAP BOM با موفقیت خوانده شد.")

            with st.expander("Data Preview (Current Shipment)"):
                st.write("LEFT (Current Packing List)")
                st.dataframe(left_df, use_container_width=True)
                st.write("RIGHT (From Balance File)")
                st.dataframe(right_df.head(10), use_container_width=True)

            # Comparison
            comparator = DatasetComparator()
            result = comparator.compare(
                left_df=left_df,
                right_df=right_df,
                mpn_lookup=mpn_lookup,
            )

            show_kpis(result["kpi_cards"])

            # Tabs for different views
            tab1, tab2, tab3 = st.tabs(["Summary & Matches", "Mismatches", "Missing/Extra"])
            
            with tab1:
                st.subheader("Reason Summary")
                st.dataframe(pd.DataFrame(result["reason_summary"]), use_container_width=True)
                st.subheader("Matched Pairs")
                st.dataframe(pd.DataFrame(result["matched_pairs"]), use_container_width=True)

            with tab2:
                st.subheader("Quantity Mismatches")
                st.dataframe(pd.DataFrame(result["qty_mismatches"]), use_container_width=True)

            with tab3:
                c1, c2 = st.columns(2)
                with c1:
                    st.write("**Missing in Right**")
                    st.dataframe(pd.DataFrame({"part_number": result["missing_in_right"]}), use_container_width=True)
                with c2:
                    st.write("**Extra in Right**")
                    st.dataframe(pd.DataFrame({"part_number": result["extra_in_right"]}), use_container_width=True)

        except Exception as e:
            st.error(f"Error: {e}")
    else:
        st.info("Please upload both files to start analysis.")
else:
    st.warning("Please select or register a product from the sidebar to continue.")