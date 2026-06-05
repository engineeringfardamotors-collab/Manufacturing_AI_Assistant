# -*- coding: utf-8 -*-
from __future__ import annotations

import io
import sys
import tempfile
from pathlib import Path
from typing import Dict

import pandas as pd
import streamlit as st

# -------------------------------------------------
# Project import bootstrap
# -------------------------------------------------
CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.engine.comparator import Comparator, CompareConfig
from services.engine.group_c_registry import GroupCRegistry


# -------------------------------------------------
# UI config
# -------------------------------------------------
st.set_page_config(
    page_title="داشبورد نهایی مغایرت پکینگ",
    page_icon="📊",
    layout="wide",
)

st.markdown(
    """
    <style>
    .stApp { direction: rtl; text-align: right; }
    .block-container { padding-top: 1rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("📊 داشبورد نهایی مغایرت پکینگ / بالانس")
st.caption("Runner Dashboard (Core Logic in Comparator.compare_from_fixed_files)")


# -------------------------------------------------
# Helpers
# -------------------------------------------------
def _excel_bytes(sheets: Dict[str, pd.DataFrame]) -> bytes:
    bio = io.BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as writer:
        for sheet_name, df in sheets.items():
            safe_name = str(sheet_name)[:31] if sheet_name else "Sheet"
            (df if df is not None else pd.DataFrame()).to_excel(writer, sheet_name=safe_name, index=False)
    bio.seek(0)
    return bio.getvalue()


def _save_uploaded_to_temp(uploaded_file, suffix: str = ".xlsx") -> str:
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.getbuffer())
        return tmp.name


# -------------------------------------------------
# Sidebar
# -------------------------------------------------
st.sidebar.header("ورودی‌ها")

partner = st.sidebar.selectbox("Partner", ["DONGFENG", "CHANGAN"], index=0)
default_shipment = 120 if partner == "DONGFENG" else 96
shipment_count = st.sidebar.number_input("تعداد خودرو محموله", min_value=1, value=default_shipment, step=1)

product_name = st.sidebar.text_input("نام محصول", value="T5 Plus1")

packing_sheet = st.sidebar.text_input("نام شیت پکینگ", value="零件层级Part Level")
balance_sheet = st.sidebar.text_input("نام شیت بالانس (اختیاری)", value="")  # اگر خالی باشد شیت اول

group_c_master_path = st.sidebar.text_input(
    "مسیر Master Group C",
    value=r"G:\AI Vibe Coding\data\master\group_c\T5_Plus1_GroupC_Master.xlsx"
)

packing_file = st.sidebar.file_uploader("فایل Packing List", type=["xlsx", "xls"])
balance_file = st.sidebar.file_uploader("فایل Balance", type=["xlsx", "xls"])
bom_file = st.sidebar.file_uploader("فایل BOM (اختیاری)", type=["xlsx", "xls"])

run_btn = st.sidebar.button("🚀 اجرای تحلیل", type="primary")


# -------------------------------------------------
# Main run
# -------------------------------------------------
if run_btn:
    try:
        if packing_file is None or balance_file is None:
            st.error("فایل‌های Packing و Balance الزامی هستند.")
            st.stop()

        # save uploaded files to temp paths
        packing_path = _save_uploaded_to_temp(packing_file, suffix=".xlsx")
        balance_path = _save_uploaded_to_temp(balance_file, suffix=".xlsx")

        # optional BOM dataframe
        bom_df = None
        if bom_file is not None:
            bom_df = pd.read_excel(bom_file)

        # load group C registry (optional but recommended)
        group_c_registry = None
        gc_path = Path(group_c_master_path)
        if gc_path.exists():
            group_c_registry = GroupCRegistry.load_from_excel(
                str(gc_path),
                product_name=product_name
            )
        else:
            st.warning("فایل Group C Master پیدا نشد. تحلیل Group C رد می‌شود.")

        # comparator config
        cfg = CompareConfig(
            product_name=product_name,
            shipment_vehicle_count_fallback=float(shipment_count),
            ratio_tolerance=1e-9,
            group_c_moq_aware=True,
        )
        comp = Comparator(cfg)

        result = comp.compare_from_fixed_files(
            packing_path=packing_path,
            balance_path=balance_path,
            bom_df=bom_df,
            group_c_registry=group_c_registry,
            packing_sheet=packing_sheet,
            balance_sheet=(balance_sheet.strip() or None),
        )

        # KPIs
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Packing Pivot Rows", result.summary.get("packing_pivot_rows", 0))
        c2.metric("A/B Mismatch", result.summary.get("ab_mismatch_rows", 0))
        c3.metric("Group C Exact", result.summary.get("group_c_exact_rows", 0))
        c4.metric("Group C Over MOQ", result.summary.get("group_c_over_moq_candidate_rows", 0))
        c5.metric("Group C Under Supply", result.summary.get("group_c_under_supply_rows", 0))

        # Notes
        with st.expander("یادداشت‌های پردازش", expanded=False):
            if result.notes:
                for n in result.notes:
                    st.write(f"- {n}")
            else:
                st.write("یادداشتی ثبت نشده است.")

        # Tabs
        tabs = st.tabs([
            "Packing Pivot",
            "Baseline Ratio",
            "A/B All",
            "A/B Mismatch",
            "Group C All",
            "Group C Exact",
            "Group C Over MOQ",
            "Group C Under Supply",
        ])

        with tabs[0]:
            st.dataframe(result.packing_pivot, use_container_width=True, height=500)
        with tabs[1]:
            st.dataframe(result.baseline_ratio, use_container_width=True, height=500)
        with tabs[2]:
            st.dataframe(result.ab_all, use_container_width=True, height=500)
        with tabs[3]:
            st.dataframe(result.ab_mismatches, use_container_width=True, height=500)
        with tabs[4]:
            st.dataframe(result.group_c_all, use_container_width=True, height=500)
        with tabs[5]:
            st.dataframe(result.group_c_exact, use_container_width=True, height=500)
        with tabs[6]:
            st.dataframe(result.group_c_over_moq_candidate, use_container_width=True, height=500)
        with tabs[7]:
            st.dataframe(result.group_c_under_supply, use_container_width=True, height=500)

        # Export
        out = _excel_bytes({
            "Packing_Pivot": result.packing_pivot,
            "Baseline_Ratio": result.baseline_ratio,
            "AB_All": result.ab_all,
            "AB_Mismatch": result.ab_mismatches,
            "GroupC_All": result.group_c_all,
            "GroupC_Exact": result.group_c_exact,
            "GroupC_Over_MOQ": result.group_c_over_moq_candidate,
            "GroupC_Under_Supply": result.group_c_under_supply,
        })

        st.download_button(
            "📥 دانلود گزارش کامل Excel",
            data=out,
            file_name=f"compare_report_{product_name.replace(' ', '_')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

        st.success("تحلیل با موفقیت انجام شد ✅")

    except Exception as e:
        st.exception(e)
else:
    st.info("فایل‌ها را بارگذاری کن و روی «اجرای تحلیل» بزن.")