# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd


@dataclass
class GroupCRegistry:
    df: Optional[pd.DataFrame] = None

    def __post_init__(self):
        if self.df is None:
            self.df = pd.DataFrame(columns=[
                "product_name",
                "main_part_no",
                "alt_part_no_1",
                "alt_part_no_2",
                "part_name",
                "consumption_ratio",
                "process_desc",
                "feed_address",
                "all_part_nos",
            ])

    @classmethod
    def empty(cls) -> "GroupCRegistry":
        return cls()

    @staticmethod
    def _norm_text(x) -> str:
        if x is None:
            return ""
        s = str(x).strip()
        s = s.replace("ي", "ی").replace("ك", "ک")
        s = s.replace("\u200c", "").replace("\u200f", "").replace("\ufeff", "")
        return s.strip()

    @staticmethod
    def _norm_part_no(x) -> str:
        s = GroupCRegistry._norm_text(x)
        if not s or s.lower() == "nan":
            return ""
        return s.upper().replace(" ", "")

    @staticmethod
    def _find_col(columns: List[str], candidates: List[str]) -> Optional[str]:
        norm_cols = [GroupCRegistry._norm_text(c).lower() for c in columns]
        norm_cands = [GroupCRegistry._norm_text(c).lower() for c in candidates]

        for cand in norm_cands:
            if cand in norm_cols:
                return columns[norm_cols.index(cand)]

        for i, col in enumerate(norm_cols):
            for cand in norm_cands:
                if cand and (cand in col or col in cand):
                    return columns[i]
        return None

    @classmethod
    def _map_columns(cls, df: pd.DataFrame) -> Dict[str, Optional[str]]:
        cols = list(df.columns)
        candidates = {
            "main_part_no": ["شماره فنی اصلی قطعه", "شماره فنی اصلی", "main part no", "main pn", "mpn", "part no", "part number", "شماره فنی"],
            "alt_part_no_1": ["شماره فنی آلترناتیو  1", "شماره فنی آلترناتیو 1", "alternative 1", "alt1", "alt 1"],
            "alt_part_no_2": ["شماره فنی آلترناتیو  2", "شماره فنی آلترناتیو 2", "alternative 2", "alt2", "alt 2"],
            "part_name": ["شرح قطعه", "نام قطعه", "part name", "description", "item description"],
            "consumption_ratio": ["ضریب مصرف", "مصرف", "qty/vehicle", "usage", "unit usage"],
            "process_desc": ["شرح پروسه", "شرح فرآیند", "فرایند", "process", "station", "line"],
            "feed_address": ["آدرس تغذیه", "feed address", "location"],
        }
        return {k: cls._find_col(cols, v) for k, v in candidates.items()}

    @classmethod
    def _read_excel_robust(cls, fp: Path) -> Tuple[pd.DataFrame, str]:
        xls = pd.ExcelFile(fp)
        sheet_names = xls.sheet_names

        preferred = ["قطعات هایلایت بنفش", "group_c", "group c", "master", "data", "sheet1"]
        ordered_sheets = []
        for p in preferred:
            for s in sheet_names:
                if cls._norm_text(s).lower() == cls._norm_text(p).lower() and s not in ordered_sheets:
                    ordered_sheets.append(s)
        for s in sheet_names:
            if s not in ordered_sheets:
                ordered_sheets.append(s)

        for s in ordered_sheets:
            for h in [0, 1, 2, 3]:
                try:
                    df = pd.read_excel(fp, sheet_name=s, header=h)
                    if df is None or df.empty:
                        continue
                    df.columns = [cls._norm_text(c) for c in df.columns]
                    mapped = cls._map_columns(df)
                    score = sum(1 for v in mapped.values() if v is not None)
                    if mapped.get("main_part_no") is not None and score >= 3:
                        return df, s
                except Exception:
                    continue

        if "قطعات هایلایت بنفش" in sheet_names:
            df = pd.read_excel(fp, sheet_name="قطعات هایلایت بنفش", header=0)
            df.columns = [cls._norm_text(c) for c in df.columns]
            return df, "قطعات هایلایت بنفش"

        raise ValueError("ساختار فایل گروه C شناسایی نشد. لطفاً هدر/شیت را بررسی کنید.")

    @classmethod
    def load_from_excel(cls, file_path: str, product_name: str) -> "GroupCRegistry":
        fp = Path(file_path)
        if not fp.exists():
            raise FileNotFoundError(f"فایل پیدا نشد: {fp}")

        raw_df, sheet_used = cls._read_excel_robust(fp)
        mapped = cls._map_columns(raw_df)

        main_col = mapped.get("main_part_no")
        if not main_col:
            raise ValueError("ستون شماره فنی اصلی قطعه پیدا نشد.")

        out = pd.DataFrame(index=raw_df.index)

        # ✅ FIX اصلی: مقدار ثابت product_name برای تمام ردیف‌ها
        out["product_name"] = str(product_name)

        out["main_part_no"] = raw_df[main_col].map(cls._norm_part_no)
        out["alt_part_no_1"] = raw_df[mapped["alt_part_no_1"]].map(cls._norm_part_no) if mapped.get("alt_part_no_1") else ""
        out["alt_part_no_2"] = raw_df[mapped["alt_part_no_2"]].map(cls._norm_part_no) if mapped.get("alt_part_no_2") else ""
        out["part_name"] = raw_df[mapped["part_name"]].map(cls._norm_text) if mapped.get("part_name") else ""
        out["consumption_ratio"] = pd.to_numeric(raw_df[mapped["consumption_ratio"]], errors="coerce") if mapped.get("consumption_ratio") else pd.NA
        out["process_desc"] = raw_df[mapped["process_desc"]].map(cls._norm_text) if mapped.get("process_desc") else ""
        out["feed_address"] = raw_df[mapped["feed_address"]].map(cls._norm_text) if mapped.get("feed_address") else ""

        out = out[out["main_part_no"].astype(str).str.len() > 0].copy()

        def build_all(row) -> List[str]:
            vals = [row.get("main_part_no", ""), row.get("alt_part_no_1", ""), row.get("alt_part_no_2", "")]
            vals = [v for v in vals if isinstance(v, str) and v.strip()]
            seen, res = set(), []
            for v in vals:
                if v not in seen:
                    seen.add(v)
                    res.append(v)
            return res

        out["all_part_nos"] = out.apply(build_all, axis=1)
        out.attrs["source_file"] = str(fp)
        out.attrs["sheet_used"] = sheet_used

        return cls(out.reset_index(drop=True))

    def stats(self, product_name: Optional[str] = None) -> Dict[str, int]:
        df = self.df if self.df is not None else pd.DataFrame()
        if product_name:
            df = df[df["product_name"] == product_name]

        total_rows = len(df)
        unique_main = df["main_part_no"].nunique() if total_rows else 0
        alt_count = 0
        if total_rows:
            alt_count = (
                (df["alt_part_no_1"].astype(str).str.len() > 0).sum()
                + (df["alt_part_no_2"].astype(str).str.len() > 0).sum()
            )

        return {
            "rows": int(total_rows),
            "unique_main_part_no": int(unique_main),
            "alternative_part_no_count": int(alt_count),
        }

    def get_product_df(self, product_name: str) -> pd.DataFrame:
        if self.df is None or self.df.empty:
            return pd.DataFrame(columns=[
                "product_name", "main_part_no", "alt_part_no_1", "alt_part_no_2",
                "part_name", "consumption_ratio", "process_desc", "feed_address", "all_part_nos"
            ])
        return self.df[self.df["product_name"] == product_name].copy()

    def as_lookup(self, product_name: str) -> Dict[str, Dict]:
        pdf = self.get_product_df(product_name)
        lookup: Dict[str, Dict] = {}

        for _, r in pdf.iterrows():
            row_info = {
                "product_name": r.get("product_name", ""),
                "main_part_no": r.get("main_part_no", ""),
                "alt_part_no_1": r.get("alt_part_no_1", ""),
                "alt_part_no_2": r.get("alt_part_no_2", ""),
                "part_name": r.get("part_name", ""),
                "consumption_ratio": r.get("consumption_ratio", pd.NA),
                "process_desc": r.get("process_desc", ""),
                "feed_address": r.get("feed_address", ""),
                "all_part_nos": r.get("all_part_nos", []),
            }
            for pn in row_info["all_part_nos"]:
                if pn:
                    lookup[pn] = row_info

        return lookup