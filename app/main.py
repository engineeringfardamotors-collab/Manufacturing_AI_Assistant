import sys
from pathlib import Path
from io import BytesIO
from datetime import datetime

import pandas as pd
import streamlit as st

# --- Path Setup ---
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.engine.comparator import Comparator
from services.engine.database_manager import DatabaseManager


# -----------------------------
# Init
# -----------------------------
db = DatabaseManager()

if "processing_complete" not in st.session_state:
    st.session_state.processing_complete = False
if "comparison_result" not in st.session_state:
    st.session_state.comparison_result = None
if "left_df" not in st.session_state:
    st.session_state.left_df = None
if "right_df" not in st.session_state:
    st.session_state.right_df = None
if "theme_mode" not in st.session_state:
    st.session_state.theme_mode = "روشن"  # روشن | تیره


# -----------------------------
# Helpers
# -----------------------------
def clean_part_number(x) -> str:
    s = "" if pd.isna(x) else str(x).strip()
    if s in ("", ".", "..", "...", "....", "-", "—", "…"):
        return ""
    return s


def read_packing_and_aggregate(
    file, shipment_units: int, product_name: str, db_manager: DatabaseManager
) -> pd.DataFrame:
    xls = pd.ExcelFile(file)
    if len(xls.sheet_names) < 2:
        raise ValueError("فایل پکینگ لیست، شیت دوم ندارد.")

    file_name_str = file.name
    om_number = file_name_str.split(" ")[0] if " " in file_name_str else file_name_str

    raw = pd.read_excel(file, sheet_name=xls.sheet_names[1])
    if raw.shape[1] < 9:
        raise ValueError("ستون‌های موردنیاز در شیت دوم فایل پکینگ یافت نشد.")

    df = pd.DataFrame(
        {
            "part_number": raw.iloc[:, 5].apply(clean_part_number),
            "alternative_part": "",
            "quantity": pd.to_numeric(raw.iloc[:, 8], errors="coerce").fillna(0),
        }
    )

    df_to_save = df[df["part_number"] != ""].copy()
    db_manager.save_packing_data(df_to_save, product_name, om_number, file_name_str)

    agg = df_to_save.groupby("part_number", as_index=False)["quantity"].sum()
    agg["quantity"] = agg["quantity"] / shipment_units
    agg["alternative_part"] = ""
    agg["description"] = ""
    agg["om_number"] = om_number

    return agg[["part_number", "alternative_part", "quantity", "description", "om_number"]].copy()


def read_balance_fixed_format(file) -> pd.DataFrame:
    xls = pd.ExcelFile(file)

    target_sheet = None
    for sh in xls.sheet_names:
        if sh.strip() == "اصلی":
            target_sheet = sh
            break
    if target_sheet is None:
        target_sheet = xls.sheet_names[0]

    raw = pd.read_excel(file, sheet_name=target_sheet, header=1)

    if raw.shape[1] < 11:
        raise ValueError("فایل بالانس: ستون‌های کافی پیدا نشد.")

    def clean_balance_part(x) -> str:
        s = "" if pd.isna(x) else str(x).strip().strip("'").strip()
        if s in ("", ".", "..", "...", "....", "-", "—", "…"):
            return ""
        return s

    mapped = pd.DataFrame(
        {
            "part_number": raw.iloc[:, 7].apply(clean_balance_part),
            "alternative_part": raw.iloc[:, 8].apply(clean_balance_part),
            "quantity": pd.to_numeric(raw.iloc[:, 10], errors="coerce").fillna(0),
            "description": "",
        }
    )

    mapped = mapped[mapped["part_number"] != ""].copy()
    return mapped


def calculate_data_quality_score(comparison_result: dict) -> float:
    total = comparison_result["summary"]["total_packing"]
    matched = comparison_result["summary"]["matched"]
    return round((matched / total * 100) if total > 0 else 0.0, 2)


def extract_qty_mismatches(comparison_result: dict, tolerance: float = 0.0001) -> list[dict]:
    out = []
    for match in comparison_result.get("matched_rows", []):
        p = match.get("packing", {})
        b = match.get("balance", {})
        p_qty = float(p.get("quantity", 0) or 0)
        b_qty = float(b.get("quantity", 0) or 0)
        if abs(p_qty - b_qty) > tolerance:
            out.append(
                {
                    "شماره قطعه": p.get("part_number", ""),
                    "تعداد پکینگ": p_qty,
                    "تعداد بالانس": b_qty,
                    "اختلاف": round(p_qty - b_qty, 6),
                    "نوع تطبیق": match.get("match_type", ""),
                }
            )
    return out


def get_part_mismatches(comparison_result: dict) -> list[dict]:
    rows = []
    for r in comparison_result.get("packing_only", []):
        rows.append(
            {
                "شماره قطعه": r.get("part_number", ""),
                "منبع": "پکینگ",
                "تعداد": r.get("quantity", 0),
            }
        )
    for r in comparison_result.get("balance_only", []):
        rows.append(
            {
                "شماره قطعه": r.get("part_number", ""),
                "منبع": "بالانس",
                "تعداد": r.get("quantity", 0),
            }
        )
    return rows


def flatten_matched_rows(comparison_result: dict) -> pd.DataFrame:
    matched_rows = comparison_result.get("matched_rows", [])
    flat = []
    for m in matched_rows:
        p = m.get("packing", {})
        b = m.get("balance", {})
        flat.append(
            {
                "part_number_packing": p.get("part_number", ""),
                "qty_packing": p.get("quantity", 0),
                "part_number_balance": b.get("part_number", ""),
                "qty_balance": b.get("quantity", 0),
                "match_type": m.get("match_type", ""),
            }
        )
    return pd.DataFrame(flat)


def to_excel_bytes(
    summary_df: pd.DataFrame,
    qty_mismatch_df: pd.DataFrame,
    part_mismatch_df: pd.DataFrame,
    matched_df: pd.DataFrame,
    left_df: pd.DataFrame,
    right_df: pd.DataFrame,
) -> bytes:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        summary_df.to_excel(writer, index=False, sheet_name="Summary")
        qty_mismatch_df.to_excel(writer, index=False, sheet_name="Qty_Mismatches")
        part_mismatch_df.to_excel(writer, index=False, sheet_name="Part_Mismatches")
        matched_df.to_excel(writer, index=False, sheet_name="Matched")
        left_df.to_excel(writer, index=False, sheet_name="Packing_Aggregated")
        right_df.to_excel(writer, index=False, sheet_name="Balance_Input")
    output.seek(0)
    return output.read()


def apply_theme(theme_mode: str):
    # روشن
    if theme_mode == "روشن":
        st.markdown(
            """
            <style>
            .stApp {
                direction: rtl;
                text-align: right;
                background: linear-gradient(135deg, #f8fbff 0%, #eef4ff 100%);
                color: #111827;
            }
            .block-container { padding-top: 1.2rem; padding-bottom: 1.2rem; }
            .main-title { font-size: 1.8rem; font-weight: 700; color: #0b3d91; margin-bottom: 0.2rem; }
            .sub-title { color: #4b5563; margin-bottom: 1rem; }
            div[data-testid="stMetric"] {
                background: #ffffff;
                border: 1px solid #e5e7eb;
                border-radius: 14px;
                padding: 10px 12px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.04);
            }
            </style>
            """,
            unsafe_allow_html=True,
        )
    # تیره
    else:
        st.markdown(
            """
            <style>
            .stApp {
                direction: rtl;
                text-align: right;
                background: linear-gradient(135deg, #0f172a 0%, #111827 100%);
                color: #e5e7eb;
            }
            .block-container { padding-top: 1.2rem; padding-bottom: 1.2rem; }
            .main-title { font-size: 1.8rem; font-weight: 700; color: #93c5fd; margin-bottom: 0.2rem; }
            .sub-title { color: #cbd5e1; margin-bottom: 1rem; }
            div[data-testid="stMetric"] {
                background: #111827;
                border: 1px solid #374151;
                border-radius: 14px;
                padding: 10px 12px;
                box-shadow: 0 2px 12px rgba(0,0,0,0.35);
            }
            </style>
            """,
            unsafe_allow_html=True,
        )


# -----------------------------
# Page Config
# -----------------------------
st.set_page_config(
    page_title="داشبورد مقایسه قطعات",
    page_icon="📊",
    layout="wide",
)

# -----------------------------
# Sidebar
# -----------------------------
with st.sidebar:
    st.header("⚙️ پیکربندی")

    theme = st.radio(
        "حالت نمایش",
        options=["روشن", "تیره"],
        index=0 if st.session_state.theme_mode == "روشن" else 1,
        horizontal=True,
    )
    st.session_state.theme_mode = theme

# Apply selected theme
apply_theme(st.session_state.theme_mode)

st.markdown('<div class="main-title">📊 داشبورد حرفه‌ای مقایسه قطعات</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-title">مقایسه پکینگ لیست مشتری با فایل بالانس داخلی + خروجی اکسل</div>',
    unsafe_allow_html=True,
)

with st.sidebar:
    all_products = db.get_all_products()
    if all_products.empty:
        st.warning("هیچ محصولی در پایگاه داده ثبت نشده است.")
        with st.expander("➕ افزودن محصول جدید", expanded=True):
            p_name = st.text_input("نام محصول")
            p_partner = st.selectbox("پارتنر", ["DONGFENG", "CHANGAN", "MG"])
            p_units = st.number_input("تعداد واحد هر محموله", min_value=1, value=120)
            if st.button("ثبت محصول", use_container_width=True):
                db.add_product(p_name, p_partner, int(p_units))
                st.success("محصول با موفقیت ثبت شد.")
                st.rerun()
        st.stop()

    product_names = all_products["product_name"].tolist()
    selected_product = st.selectbox("انتخاب محصول", product_names, index=0)

    selected_row = all_products[all_products["product_name"] == selected_product].iloc[0]
    shipment_units = int(selected_row["shipment_units"])
    st.info(f"پارتنر: {selected_row['partner']}\nواحد محموله: {shipment_units}")

    with st.expander("➕ افزودن محصول جدید"):
        n_name = st.text_input("نام", key="new_prod_name")
        n_partner = st.selectbox("پارتنر", ["DONGFENG", "CHANGAN", "MG"], key="new_prod_partner")
        n_units = st.number_input("واحد", min_value=1, value=120, key="new_prod_units")
        if st.button("ثبت", key="btn_new_prod", use_container_width=True):
            db.add_product(n_name, n_partner, int(n_units))
            st.success("محصول جدید ثبت شد.")
            st.rerun()

    st.divider()
    st.caption("فایل‌ها را بارگذاری کنید:")
    left_file = st.file_uploader("📥 فایل پکینگ لیست", type=["xlsx", "xls"], key="left_file")
    right_file = st.file_uploader("📥 فایل بالانس", type=["xlsx", "xls"], key="right_file")
    mpn_file = st.file_uploader("اختیاری: SAP MPN", type=["xlsx", "xls"], key="mpn_file")
    bom_file = st.file_uploader("اختیاری: SAP BOM", type=["xlsx", "xls"], key="bom_file")

    process_clicked = st.button("🚀 پردازش و نمایش", use_container_width=True)

# -----------------------------
# Processing
# -----------------------------
if process_clicked:
    if not left_file or not right_file:
        st.warning("لطفاً هر دو فایل پکینگ و بالانس را آپلود کنید.")
    else:
        try:
            left_df = read_packing_and_aggregate(left_file, shipment_units, selected_product, db)
            right_df = read_balance_fixed_format(right_file)

            comparator = Comparator()
            result = comparator.compare_parts(
                packing_list_df=left_df,
                balance_df=right_df,
                packing_part_col="part_number",
                balance_part_col="part_number",
            )

            st.session_state.left_df = left_df
            st.session_state.right_df = right_df
            st.session_state.comparison_result = result
            st.session_state.processing_complete = True

            if mpn_file is not None:
                st.info("فایل MPN بارگذاری شد (پردازش آن فعلاً غیرفعال است).")
            if bom_file is not None:
                st.info("فایل BOM بارگذاری شد (این بخش در نسخه بعدی تکمیل می‌شود).")

        except Exception as e:
            st.session_state.processing_complete = False
            st.error(f"خطا در پردازش: {e}")

# -----------------------------
# Main Result Area
# -----------------------------
if st.session_state.processing_complete and st.session_state.comparison_result:
    result = st.session_state.comparison_result
    summary = result["summary"]

    quality_score = calculate_data_quality_score(result)
    qty_mismatches = extract_qty_mismatches(result)
    part_mismatches = get_part_mismatches(result)
    matched_df = flatten_matched_rows(result)

    summary_df = pd.DataFrame(
        [
            {"شاخص": "کل ردیف پکینگ", "مقدار": summary.get("total_packing", 0)},
            {"شاخص": "کل ردیف بالانس", "مقدار": summary.get("total_balance", 0)},
            {"شاخص": "تعداد تطابق", "مقدار": summary.get("matched", 0)},
            {"شاخص": "فقط در پکینگ", "مقدار": summary.get("packing_only", 0)},
            {"شاخص": "فقط در بالانس", "مقدار": summary.get("balance_only", 0)},
            {"شاخص": "امتیاز کیفیت داده (%)", "مقدار": quality_score},
        ]
    )
    qty_mismatch_df = pd.DataFrame(qty_mismatches)
    part_mismatch_df = pd.DataFrame(part_mismatches)

    # KPI
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("کل ردیف‌های پکینگ", summary.get("total_packing", 0))
    c2.metric("تعداد تطابق", summary.get("matched", 0))
    c3.metric("عدم تطابق", summary.get("packing_only", 0) + summary.get("balance_only", 0))
    c4.metric("امتیاز کیفیت داده", f"{quality_score}%")

    # Export Excel
    excel_bytes = to_excel_bytes(
        summary_df=summary_df,
        qty_mismatch_df=qty_mismatch_df,
        part_mismatch_df=part_mismatch_df,
        matched_df=matched_df,
        left_df=st.session_state.left_df if st.session_state.left_df is not None else pd.DataFrame(),
        right_df=st.session_state.right_df if st.session_state.right_df is not None else pd.DataFrame(),
    )
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"comparison_report_{selected_product}_{ts}.xlsx"

    st.download_button(
        label="📤 خروجی اکسل گزارش مغایرت‌ها",
        data=excel_bytes,
        file_name=file_name,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

    st.divider()

    with st.expander("👀 پیش‌نمایش داده‌های ورودی"):
        lcol, rcol = st.columns(2)
        with lcol:
            st.markdown("**پکینگ (تجمیع‌شده)**")
            st.dataframe(st.session_state.left_df, use_container_width=True, height=260)
        with rcol:
            st.markdown("**بالانس**")
            st.dataframe(st.session_state.right_df, use_container_width=True, height=260)

    st.divider()

    tab1, tab2, tab3, tab4 = st.tabs(
        ["📌 خلاصه", "⚖️ مغایرت کمیت", "🧩 مغایرت شماره قطعه", "📋 اقلام تطبیق‌شده"]
    )

    with tab1:
        st.markdown("### خلاصه وضعیت")
        st.dataframe(summary_df, use_container_width=True, hide_index=True)

    with tab2:
        st.markdown("### مغایرت‌های کمیت")
        if not qty_mismatch_df.empty:
            st.dataframe(qty_mismatch_df, use_container_width=True, hide_index=True)
        else:
            st.success("مغایرت کمیتی مشاهده نشد.")

    with tab3:
        st.markdown("### مغایرت شماره قطعه")
        if not part_mismatch_df.empty:
            st.dataframe(part_mismatch_df, use_container_width=True, hide_index=True)
        else:
            st.success("مغایرت شماره قطعه مشاهده نشد.")

    with tab4:
        st.markdown("### اقلام تطبیق‌شده")
        if not matched_df.empty:
            st.dataframe(matched_df, use_container_width=True, hide_index=True)
        else:
            st.info("رکورد تطبیق‌شده‌ای وجود ندارد.")

else:
    st.info("برای شروع، محصول را انتخاب کرده و فایل‌ها را بارگذاری کنید.")