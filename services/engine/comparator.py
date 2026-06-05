# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from services.engine.group_c_registry import GroupCRegistry


@dataclass
class CompareConfig:
    product_name: str = "T5 Plus1"

    packing_part_no_col: str = "part_no"
    packing_qty_col: str = "qty"
    packing_shipment_vehicle_count_col: Optional[str] = "shipment_vehicle_count"

    balance_part_no_col: str = "part_no"
    balance_ratio_col: Optional[str] = "consumption_ratio"
    balance_qty_col: Optional[str] = "qty"
    balance_vehicle_count_col: Optional[str] = "vehicle_count"

    bom_part_no_col: Optional[str] = "part_no"
    bom_ratio_col: Optional[str] = "consumption_ratio"
    bom_qty_col: Optional[str] = None
    bom_vehicle_count_col: Optional[str] = None

    ratio_tolerance: float = 1e-9
    group_c_moq_aware: bool = True
    shipment_vehicle_count_fallback: Optional[float] = None


@dataclass
class CompareResult:
    summary: Dict[str, int]
    packing_pivot: pd.DataFrame
    baseline_ratio: pd.DataFrame
    ab_all: pd.DataFrame
    ab_mismatches: pd.DataFrame
    group_c_all: pd.DataFrame
    group_c_exact: pd.DataFrame
    group_c_over_moq_candidate: pd.DataFrame
    group_c_under_supply: pd.DataFrame
    notes: List[str]


class Comparator:
    def __init__(self, config: Optional[CompareConfig] = None):
        self.config = config or CompareConfig()

    @staticmethod
    def _norm_text(x) -> str:
        if x is None:
            return ""
        s = str(x).strip()
        s = s.replace("ي", "ی").replace("ك", "ک")
        s = s.replace("\u200c", " ").replace("\u200f", "").replace("\ufeff", "")
        s = " ".join(s.split())
        return s.strip()

    @classmethod
    def _norm_part_no(cls, x) -> str:
        s = cls._norm_text(x)
        if not s or s.lower() == "nan":
            return ""
        return s.upper().replace(" ", "")

    @staticmethod
    def _safe_series(df: pd.DataFrame, col: Optional[str], default=np.nan) -> pd.Series:
        if col and col in df.columns:
            return df[col]
        return pd.Series([default] * len(df), index=df.index)

    @staticmethod
    def _to_num(s: pd.Series) -> pd.Series:
        return pd.to_numeric(s, errors="coerce")

    @staticmethod
    def _idx_from_excel_col(letter: str) -> int:
        letter = letter.strip().upper()
        n = 0
        for ch in letter:
            n = n * 26 + (ord(ch) - ord("A") + 1)
        return n - 1

    @staticmethod
    def _find_col(cols: List[str], keys: List[str]) -> Optional[str]:
        ncols = [str(c).strip().lower() for c in cols]
        for k in keys:
            kk = str(k).strip().lower()
            for i, c in enumerate(ncols):
                if kk == c or kk in c:
                    return cols[i]
        return None

    @staticmethod
    def _contains_all_tokens(text: str, tokens: List[str]) -> bool:
        t = str(text).lower()
        return all(tok in t for tok in tokens)

    def _find_main_part_col_fa(self, cols: List[str]) -> Optional[str]:
        for c in cols:
            nc = self._norm_text(c).lower()
            if "جایگزین" in nc:
                continue
            if self._contains_all_tokens(nc, ["شماره", "فنی"]):
                return c
        return self._find_col(cols, ["main part no", "main part number", "part number", "part no"])

    def _find_alt_part_col_fa(self, cols: List[str]) -> Optional[str]:
        for c in cols:
            nc = self._norm_text(c).lower()
            if self._contains_all_tokens(nc, ["شماره", "فنی"]) and ("جایگزین" in nc):
                return c
        return self._find_col(cols, ["alt part no", "alternative part", "substitute part", "alternate part"])

    def read_packing_fixed_index(self, packing_path: str, sheet_name: str = "零件层级Part Level", part_no_col_letter: str = "F") -> pd.DataFrame:
        df = pd.read_excel(packing_path, sheet_name=sheet_name)
        df.columns = [self._norm_text(c) for c in df.columns]

        part_idx = self._idx_from_excel_col(part_no_col_letter)
        if part_idx >= len(df.columns):
            raise ValueError(f"Packing column {part_no_col_letter} خارج از محدوده ستون‌هاست.")

        part_no = df.iloc[:, part_idx].map(self._norm_part_no)

        qty_col = self._find_col(df.columns.tolist(), ["Part Qty", "Qty", "Quantity", "用量"])
        if qty_col:
            qty = pd.to_numeric(df[qty_col], errors="coerce").fillna(0)
        else:
            cand = None
            for j in range(part_idx, min(part_idx + 6, len(df.columns))):
                s = pd.to_numeric(df.iloc[:, j], errors="coerce")
                if s.notna().sum() > 0:
                    cand = s.fillna(0)
                    break
            if cand is None:
                raise ValueError("ستون Part Qty پیدا نشد.")
            qty = cand

        desc_col = self._find_col(df.columns.tolist(), ["Part Description", "Description", "零件描述", "零件名称", "شرح"])
        if desc_col:
            desc = df[desc_col].map(self._norm_text)
        else:
            g_idx = self._idx_from_excel_col("G")
            desc = df.iloc[:, g_idx].map(self._norm_text) if g_idx < len(df.columns) else ""

        out = pd.DataFrame({"part_no": part_no, "part_desc": desc, "qty": qty})
        out = out[out["part_no"].str.len() > 0].copy()
        return out

    def read_balance_fixed_index(self, balance_path: str, sheet_name: Optional[str] = None, main_col_letter: str = "H", alt_col_letter: str = "I") -> pd.DataFrame:
        xls = pd.ExcelFile(balance_path)
        sh = sheet_name or xls.sheet_names[0]
        df = pd.read_excel(balance_path, sheet_name=sh)
        df.columns = [self._norm_text(c) for c in df.columns]
        cols = df.columns.tolist()

        main_col = self._find_main_part_col_fa(cols)
        alt_col = self._find_alt_part_col_fa(cols)

        main_idx = self._idx_from_excel_col(main_col_letter)
        alt_idx = self._idx_from_excel_col(alt_col_letter)

        if main_col and main_col in df.columns:
            main_no = df[main_col].map(self._norm_part_no)
            main_pos = cols.index(main_col)
        else:
            if main_idx >= len(cols):
                raise ValueError("ستون شماره فنی اصلی پیدا نشد (نه هدر فارسی/انگلیسی، نه H).")
            main_no = df.iloc[:, main_idx].map(self._norm_part_no)
            main_pos = main_idx

        if alt_col and alt_col in df.columns:
            alt_no = df[alt_col].map(self._norm_part_no)
            alt_pos = cols.index(alt_col)
        else:
            alt_no = df.iloc[:, alt_idx].map(self._norm_part_no) if alt_idx < len(cols) else ""
            alt_pos = alt_idx if alt_idx < len(cols) else main_pos + 1

        ratio_col = self._find_col(cols, ["Consumption Ratio", "Part Qty", "Qty", "Quantity", "用量", "ضریب مصرف", "نسبت مصرف", "Ratio"])
        if ratio_col:
            ratio = pd.to_numeric(df[ratio_col], errors="coerce")
        else:
            start = min(main_pos, alt_pos)
            cand = None
            for j in range(start, min(start + 12, len(cols))):
                if j in (main_pos, alt_pos):
                    continue
                s = pd.to_numeric(df.iloc[:, j], errors="coerce")
                if s.notna().sum() > 0:
                    cand = s
                    break
            if cand is None:
                raise ValueError("ستون ratio در Balance پیدا نشد (header/fallback).")
            ratio = cand

        ratio = pd.to_numeric(ratio, errors="coerce").fillna(0)

        desc_col = self._find_col(cols, ["Part Description", "Description", "零件描述", "零件名称", "شرح"])
        if desc_col:
            desc = df[desc_col].map(self._norm_text)
        else:
            j_idx = self._idx_from_excel_col("J")
            desc = df.iloc[:, j_idx].map(self._norm_text) if j_idx < len(cols) else ""

        out = pd.DataFrame({
            "main_part_no": main_no,
            "alt_part_no": alt_no,
            "part_desc": desc,
            "consumption_ratio": ratio,
        })
        out = out[out["main_part_no"].str.len() > 0].copy()
        return out

    def _build_packing_pivot(self, packing_df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
        c = self.config
        notes: List[str] = []

        df = packing_df.copy()
        df["part_no_norm"] = self._safe_series(df, c.packing_part_no_col, "").map(self._norm_part_no)
        df["qty_num"] = self._to_num(self._safe_series(df, c.packing_qty_col, 0)).fillna(0)

        if c.packing_shipment_vehicle_count_col and c.packing_shipment_vehicle_count_col in df.columns:
            svc = self._to_num(df[c.packing_shipment_vehicle_count_col]).replace(0, np.nan)
            df["shipment_vehicle_count"] = svc
            notes.append(f"shipment_vehicle_count from packing column: {c.packing_shipment_vehicle_count_col}")
        else:
            fallback = c.shipment_vehicle_count_fallback
            if fallback is None or fallback == 0:
                raise ValueError("Shipment vehicle count not found in packing and no fallback provided.")
            df["shipment_vehicle_count"] = float(fallback)
            notes.append(f"shipment_vehicle_count fallback used: {fallback}")

        df = df[df["part_no_norm"].str.len() > 0].copy()

        pivot = df.groupby("part_no_norm", as_index=False).agg(
            packing_qty=("qty_num", "sum"),
            shipment_vehicle_count=("shipment_vehicle_count", "max"),
        )
        pivot["packing_ratio"] = pivot["packing_qty"] / pivot["shipment_vehicle_count"]
        return pivot, notes

    def _ratio_from_source(self, df: Optional[pd.DataFrame], part_col: Optional[str], ratio_col: Optional[str], qty_col: Optional[str], veh_col: Optional[str], src_name: str) -> pd.DataFrame:
        if df is None or df.empty or not part_col or part_col not in df.columns:
            return pd.DataFrame(columns=["part_no_norm", f"{src_name}_ratio"])

        x = df.copy()
        x["part_no_norm"] = self._safe_series(x, part_col, "").map(self._norm_part_no)
        x = x[x["part_no_norm"].str.len() > 0].copy()

        if ratio_col and ratio_col in x.columns:
            x[f"{src_name}_ratio"] = self._to_num(x[ratio_col])
        else:
            if not qty_col or qty_col not in x.columns:
                x[f"{src_name}_ratio"] = np.nan
            else:
                qty = self._to_num(x[qty_col]).fillna(0)
                if veh_col and veh_col in x.columns:
                    veh = self._to_num(x[veh_col]).replace(0, np.nan)
                    x[f"{src_name}_ratio"] = qty / veh
                else:
                    x[f"{src_name}_ratio"] = np.nan

        return x.groupby("part_no_norm", as_index=False)[f"{src_name}_ratio"].mean()

    def _build_baseline_ratio(self, balance_df: Optional[pd.DataFrame], bom_df: Optional[pd.DataFrame]) -> pd.DataFrame:
        c = self.config
        bal = self._ratio_from_source(balance_df, c.balance_part_no_col, c.balance_ratio_col, c.balance_qty_col, c.balance_vehicle_count_col, "balance")
        bom = self._ratio_from_source(bom_df, c.bom_part_no_col, c.bom_ratio_col, c.bom_qty_col, c.bom_vehicle_count_col, "bom")
        merged = bal.merge(bom, on="part_no_norm", how="outer")
        bom_s = merged["bom_ratio"] if "bom_ratio" in merged.columns else pd.Series(np.nan, index=merged.index)
        bal_s = merged["balance_ratio"] if "balance_ratio" in merged.columns else pd.Series(np.nan, index=merged.index)
        merged["baseline_ratio"] = np.where(bom_s.notna(), bom_s, bal_s)
        merged["baseline_ratio"] = pd.to_numeric(merged["baseline_ratio"], errors="coerce")
        return merged

    def _compare_group_c(self, packing_pivot: pd.DataFrame, group_c_registry: GroupCRegistry) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        c = self.config
        tol = c.ratio_tolerance
        lookup = group_c_registry.as_lookup(c.product_name)

        rows: List[Dict] = []
        for _, r in packing_pivot.iterrows():
            pn = r["part_no_norm"]
            hit = lookup.get(pn)
            if hit is None:
                continue

            master_ratio = pd.to_numeric(hit.get("consumption_ratio", np.nan), errors="coerce")
            packing_ratio = pd.to_numeric(r["packing_ratio"], errors="coerce")
            ratio_diff = packing_ratio - master_ratio if pd.notna(master_ratio) and pd.notna(packing_ratio) else np.nan
            abs_diff = abs(ratio_diff) if pd.notna(ratio_diff) else np.nan

            match_type = "main"
            if pn == self._norm_part_no(hit.get("alt_part_no_1", "")) or pn == self._norm_part_no(hit.get("alt_part_no_2", "")):
                match_type = "alternative"

            if pd.isna(abs_diff):
                status = "unknown"
            elif abs_diff <= tol:
                status = "exact"
            elif ratio_diff > tol:
                status = "over_moq_candidate" if c.group_c_moq_aware else "mismatch_over"
            else:
                status = "under_supply"

            rows.append({
                "product_name": c.product_name,
                "packing_part_no": pn,
                "group_c_main_part_no": hit.get("main_part_no", ""),
                "match_type": match_type,
                "part_name": hit.get("part_name", ""),
                "process_desc": hit.get("process_desc", ""),
                "feed_address": hit.get("feed_address", ""),
                "shipment_vehicle_count": r["shipment_vehicle_count"],
                "packing_qty": r["packing_qty"],
                "packing_ratio": packing_ratio,
                "master_ratio": master_ratio,
                "ratio_diff": ratio_diff,
                "abs_ratio_diff": abs_diff,
                "status": status,
            })

        all_df = pd.DataFrame(rows)
        if all_df.empty:
            empty = pd.DataFrame(columns=["product_name", "packing_part_no", "group_c_main_part_no", "match_type", "part_name", "process_desc", "feed_address", "shipment_vehicle_count", "packing_qty", "packing_ratio", "master_ratio", "ratio_diff", "abs_ratio_diff", "status"])
            return empty, empty.copy(), empty.copy(), empty.copy()

        return (
            all_df,
            all_df[all_df["status"] == "exact"].copy(),
            all_df[all_df["status"] == "over_moq_candidate"].copy(),
            all_df[all_df["status"] == "under_supply"].copy(),
        )

    def _compare_ab_strict(self, packing_pivot: pd.DataFrame, baseline_ratio_df: pd.DataFrame, group_c_registry: Optional[GroupCRegistry]) -> Tuple[pd.DataFrame, pd.DataFrame]:
        tol = self.config.ratio_tolerance
        merged = packing_pivot.merge(baseline_ratio_df[["part_no_norm", "baseline_ratio"]], on="part_no_norm", how="left")

        group_c_set = set()
        if group_c_registry is not None and group_c_registry.df is not None and not group_c_registry.df.empty:
            for _, rr in group_c_registry.df.iterrows():
                for pn in rr.get("all_part_nos", []):
                    if pn:
                        group_c_set.add(self._norm_part_no(pn))

        merged["is_group_c"] = merged["part_no_norm"].isin(group_c_set)
        ab = merged[~merged["is_group_c"]].copy()
        ab["ratio_diff"] = ab["packing_ratio"] - ab["baseline_ratio"]
        ab["abs_ratio_diff"] = ab["ratio_diff"].abs()
        ab["status"] = np.where(ab["baseline_ratio"].isna(), "missing_baseline", np.where(ab["abs_ratio_diff"] <= tol, "exact", "mismatch"))
        return ab, ab[ab["status"].isin(["mismatch", "missing_baseline"])].copy()

    def compare(self, packing_df: pd.DataFrame, balance_df: Optional[pd.DataFrame] = None, bom_df: Optional[pd.DataFrame] = None, group_c_registry: Optional[GroupCRegistry] = None) -> CompareResult:
        notes: List[str] = []
        packing_pivot, pivot_notes = self._build_packing_pivot(packing_df)
        notes.extend(pivot_notes)
        baseline = self._build_baseline_ratio(balance_df, bom_df)

        if group_c_registry is not None:
            gc_all, gc_exact, gc_over, gc_under = self._compare_group_c(packing_pivot, group_c_registry)
        else:
            gc_all = pd.DataFrame()
            gc_exact = pd.DataFrame()
            gc_over = pd.DataFrame()
            gc_under = pd.DataFrame()
            notes.append("group_c_registry not provided; Group C analysis skipped.")

        ab_all, ab_mismatches = self._compare_ab_strict(packing_pivot, baseline, group_c_registry)

        summary = {
            "packing_pivot_rows": int(len(packing_pivot)),
            "baseline_rows": int(len(baseline)),
            "ab_rows": int(len(ab_all)),
            "ab_mismatch_rows": int(len(ab_mismatches)),
            "group_c_rows": int(len(gc_all)),
            "group_c_exact_rows": int(len(gc_exact)),
            "group_c_over_moq_candidate_rows": int(len(gc_over)),
            "group_c_under_supply_rows": int(len(gc_under)),
        }

        return CompareResult(summary, packing_pivot, baseline, ab_all, ab_mismatches, gc_all, gc_exact, gc_over, gc_under, notes)

    # ================= Legacy =================
    @staticmethod
    def _legacy_normalize_part(part) -> str:
        if part is None:
            return ""
        s = str(part).strip().upper()
        if not s or s == "NAN":
            return ""
        import re
        s = re.sub(r"[-_/]REV\d+$", "", s, flags=re.IGNORECASE)
        s = re.sub(r"[-_/]R\d+$", "", s, flags=re.IGNORECASE)
        s = re.sub(r"[^A-Z0-9]", "", s)
        return s

    @staticmethod
    def _legacy_variants(norm: str) -> set:
        if not norm:
            return set()
        variants = {norm}
        for p in ("PART", "ITEM", "P"):
            if norm.startswith(p) and len(norm) > len(p):
                variants.add(norm[len(p):])
        variants.add(norm.lstrip("0") or "0")
        digits = "".join(ch for ch in norm if ch.isdigit())
        if digits:
            variants.add(digits.lstrip("0") or "0")
        return {v for v in variants if v}

    def compare_parts(self, packing_df: pd.DataFrame, balance_df: pd.DataFrame, packing_part_col: str = "Part Number", balance_part_col: str = "Part Number") -> Dict[str, object]:
        if packing_df is None or packing_df.empty:
            return {
                "summary": {"matched": 0, "packing_only": 0, "balance_only": 0},
                "matches": [],
                "matched_rows": [],
                "packing_only": [],
                "balance_only": [],
            }
        if balance_df is None or balance_df.empty:
            p_only = [self._legacy_normalize_part(v) for v in packing_df.get(packing_part_col, pd.Series(dtype=object)).tolist()]
            p_only = [x for x in p_only if x]
            return {
                "summary": {"matched": 0, "packing_only": len(p_only), "balance_only": 0},
                "matches": [],
                "matched_rows": [],
                "packing_only": p_only,
                "balance_only": [],
            }

        p_rows = []
        for i in range(len(packing_df)):
            raw = packing_df.iloc[i][packing_part_col] if packing_part_col in packing_df.columns else None
            norm = self._legacy_normalize_part(raw)
            if not norm:
                continue
            p_rows.append({
                "idx": i,
                "norm": norm,
                "variants": self._legacy_variants(norm),
                "row": packing_df.iloc[i].to_dict(),
            })

        b_rows = []
        for i in range(len(balance_df)):
            raw = balance_df.iloc[i][balance_part_col] if balance_part_col in balance_df.columns else None
            norm = self._legacy_normalize_part(raw)
            if not norm:
                continue
            b_rows.append({
                "idx": i,
                "norm": norm,
                "variants": self._legacy_variants(norm),
                "row": balance_df.iloc[i].to_dict(),
            })

        used_b = set()
        matches = []
        matched_rows = []

        # exact
        for p in p_rows:
            found = None
            for bi, b in enumerate(b_rows):
                if bi in used_b:
                    continue
                if p["norm"] == b["norm"]:
                    found = bi
                    break
            if found is not None:
                used_b.add(found)
                b = b_rows[found]
                matches.append({
                    "packing_index": p["idx"],
                    "balance_index": b["idx"],
                    "packing_part": p["norm"],
                    "balance_part": b["norm"],
                    "match_type": "exact",
                })
                matched_rows.append({
                    "packing": p["row"],   # <-- برای تست Qty
                    "balance": b["row"],   # <-- برای تست Qty
                    "packing_part": p["norm"],
                    "balance_part": b["norm"],
                    "match_type": "exact",
                })

        # variant
        matched_p_idx = {m["packing_index"] for m in matches}
        for p in p_rows:
            if p["idx"] in matched_p_idx:
                continue
            found = None
            for bi, b in enumerate(b_rows):
                if bi in used_b:
                    continue
                if p["variants"].intersection(b["variants"]):
                    found = bi
                    break
            if found is not None:
                used_b.add(found)
                b = b_rows[found]
                matches.append({
                    "packing_index": p["idx"],
                    "balance_index": b["idx"],
                    "packing_part": p["norm"],
                    "balance_part": b["norm"],
                    "match_type": "variant",
                })
                matched_rows.append({
                    "packing": p["row"],
                    "balance": b["row"],
                    "packing_part": p["norm"],
                    "balance_part": b["norm"],
                    "match_type": "variant",
                })

        matched_p_idx = {m["packing_index"] for m in matches}
        packing_only = [p["norm"] for p in p_rows if p["idx"] not in matched_p_idx]
        balance_only = [b["norm"] for bi, b in enumerate(b_rows) if bi not in used_b]

        return {
            "summary": {
                "matched": len(matches),
                "packing_only": len(packing_only),
                "balance_only": len(balance_only),
            },
            "matches": matches,
            "matched_rows": matched_rows,
            "packing_only": packing_only,
            "balance_only": balance_only,
        }

    def compare_from_fixed_files(
        self,
        packing_path: str,
        balance_path: str,
        bom_df: Optional[pd.DataFrame] = None,
        group_c_registry: Optional[GroupCRegistry] = None,
        packing_sheet: str = "零件层级Part Level",
        balance_sheet: Optional[str] = None,
    ) -> CompareResult:
        packing_df = self.read_packing_fixed_index(packing_path=packing_path, sheet_name=packing_sheet, part_no_col_letter="F")
        balance_fixed = self.read_balance_fixed_index(balance_path=balance_path, sheet_name=balance_sheet, main_col_letter="H", alt_col_letter="I")

        balance_baseline = balance_fixed.rename(columns={"main_part_no": "part_no", "consumption_ratio": "consumption_ratio"})[["part_no", "consumption_ratio"]].copy()

        self.config.packing_part_no_col = "part_no"
        self.config.packing_qty_col = "qty"
        self.config.balance_part_no_col = "part_no"
        self.config.balance_ratio_col = "consumption_ratio"

        return self.compare(
            packing_df=packing_df,
            balance_df=balance_baseline,
            bom_df=bom_df,
            group_c_registry=group_c_registry,
        )