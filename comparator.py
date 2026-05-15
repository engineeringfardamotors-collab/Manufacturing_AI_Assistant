import re
import pandas as pd

from services.engine.alternative_resolver import AlternativePartResolver


class DatasetComparator:
    SUFFIX_PATTERN = re.compile(r"^(.+)-L\d{2}$", re.IGNORECASE)

    def __init__(self):
        self.resolver = AlternativePartResolver()

    def compare(
        self,
        left_df: pd.DataFrame,
        right_df: pd.DataFrame,
        mpn_lookup: dict | None = None,
    ) -> dict:
        """
        مقایسه دو DataFrame.
        mpn_lookup: نتیجه SapMpnReader.build_lookup() — اختیاری
            {
              "mpn_to_internal": {mpn_part -> internal_part},
              "internal_to_mpns": {internal_part -> [mpn_parts]}
            }
        """
        # --- Pre-process: build lookup structures (O(n)) ---
        left_parts_all = sorted(set(left_df["part_number"].dropna().astype(str).str.strip()))
        right_parts_all = sorted(set(right_df["part_number"].dropna().astype(str).str.strip()))

        # Build deleted sets (O(n) scan once)
        left_deleted = self._build_deleted_set(left_df)
        right_deleted = self._build_deleted_set(right_df)

        left_parts = [p for p in left_parts_all if p not in left_deleted]
        right_parts = [p for p in right_parts_all if p not in right_deleted]

        right_parts_set = set(right_parts)

        # Build alternative lookup from right_df: alternative_part -> part_number (O(n))
        alt_to_right = {}  # alt_value -> right part_number
        if "alternative_part" in right_df.columns:
            for _, row in right_df[["part_number", "alternative_part"]].drop_duplicates().iterrows():
                rp = str(row["part_number"]).strip()
                alt = str(row["alternative_part"]).strip() if pd.notna(row["alternative_part"]) else ""
                if alt and alt not in ("", "nan", "None"):
                    alt_to_right[alt] = rp

        # Build alternative lookup from left_df: left part -> its alternative
        left_alt_map = {}  # left_part -> alternative_part
        if "alternative_part" in left_df.columns:
            for _, row in left_df[["part_number", "alternative_part"]].drop_duplicates().iterrows():
                lp = str(row["part_number"]).strip()
                alt = str(row["alternative_part"]).strip() if pd.notna(row["alternative_part"]) else ""
                if alt and alt not in ("", "nan", "None"):
                    left_alt_map[lp] = alt

        # Build suffix base map for right parts (O(n))
        right_base_map = {}  # base -> right_part_number
        for rp in right_parts:
            m = self.SUFFIX_PATTERN.match(rp)
            if m:
                base = m.group(1)
                right_base_map.setdefault(base, rp)
        # Also map exact part as its own base
        for rp in right_parts:
            right_base_map.setdefault(rp, rp)

        matched_pairs = []
        missing_in_right = []
        used_right_parts = set()

        # --- Pass 1: Exact match O(1) ---
        unmatched_left = []
        for left_part in left_parts:
            if left_part in right_parts_set and left_part not in used_right_parts:
                used_right_parts.add(left_part)
                matched_pairs.append({
                    "left_part_number": left_part,
                    "right_part_number": left_part,
                    "reason": "exact",
                })
            else:
                unmatched_left.append(left_part)

        # --- Pass 2: Alternative match O(n) ---
        still_unmatched = []
        for left_part in unmatched_left:
            matched = False

            # آیا left_part به عنوان alternative در right تعریف شده؟
            if left_part in alt_to_right:
                rp = alt_to_right[left_part]
                if rp in right_parts_set and rp not in used_right_parts:
                    used_right_parts.add(rp)
                    matched_pairs.append({
                        "left_part_number": left_part,
                        "right_part_number": rp,
                        "reason": "alternative_part",
                    })
                    matched = True

            # آیا alternative خود left_part در right هست؟
            if not matched and left_part in left_alt_map:
                alt = left_alt_map[left_part]
                if alt in right_parts_set and alt not in used_right_parts:
                    used_right_parts.add(alt)
                    matched_pairs.append({
                        "left_part_number": left_part,
                        "right_part_number": alt,
                        "reason": "alternative_part",
                    })
                    matched = True

            if not matched:
                still_unmatched.append(left_part)

        # --- Pass 2.5: SAP MPN match O(n) ---
        still_unmatched_2 = []
        if mpn_lookup:
            mpn_to_internal = mpn_lookup.get("mpn_to_internal", {})
            internal_to_mpns = mpn_lookup.get("internal_to_mpns", {})

            for left_part in still_unmatched:
                matched = False

                # case A: left_part یک MPN است → internal آن در right هست؟
                if left_part in mpn_to_internal:
                    internal = mpn_to_internal[left_part]
                    if internal in right_parts_set and internal not in used_right_parts:
                        used_right_parts.add(internal)
                        matched_pairs.append({
                            "left_part_number": left_part,
                            "right_part_number": internal,
                            "reason": "sap_mpn",
                        })
                        matched = True

                # case B: left_part یک internal است → یکی از MPN‌هایش در right هست؟
                if not matched and left_part in internal_to_mpns:
                    for mpn in internal_to_mpns[left_part]:
                        if mpn in right_parts_set and mpn not in used_right_parts:
                            used_right_parts.add(mpn)
                            matched_pairs.append({
                                "left_part_number": left_part,
                                "right_part_number": mpn,
                                "reason": "sap_mpn",
                            })
                            matched = True
                            break

                # case C: left_part در right نیست اما internal آن در right هست (از طریق base)
                if not matched:
                    lm = self.SUFFIX_PATTERN.match(left_part)
                    if lm:
                        left_base = lm.group(1)
                        # آیا این base یک internal در MPN است؟
                        if left_base in right_parts_set and left_base not in used_right_parts:
                            used_right_parts.add(left_base)
                            matched_pairs.append({
                                "left_part_number": left_part,
                                "right_part_number": left_base,
                                "reason": "sap_mpn",
                            })
                            matched = True

                if not matched:
                    still_unmatched_2.append(left_part)
        else:
            still_unmatched_2 = still_unmatched

        # --- Pass 3: Suffix match O(n) ---
        for left_part in still_unmatched_2:
            matched = False
            lm = self.SUFFIX_PATTERN.match(left_part)
            left_base = lm.group(1) if lm else left_part

            # آیا base در right هست؟
            if left_base in right_parts_set and left_base not in used_right_parts:
                used_right_parts.add(left_base)
                matched_pairs.append({
                    "left_part_number": left_part,
                    "right_part_number": left_base,
                    "reason": "suffix_based",
                })
                matched = True

            # آیا right part با همین base وجود دارد؟
            if not matched and left_base in right_base_map:
                rp = right_base_map[left_base]
                if rp not in used_right_parts and rp in right_parts_set:
                    used_right_parts.add(rp)
                    matched_pairs.append({
                        "left_part_number": left_part,
                        "right_part_number": rp,
                        "reason": "suffix_based",
                    })
                    matched = True

            # آیا left_part به عنوان base یک right part suffix-dار هست؟
            if not matched:
                for rp in right_parts:
                    if rp in used_right_parts:
                        continue
                    rm = self.SUFFIX_PATTERN.match(rp)
                    if rm and rm.group(1) == left_part:
                        used_right_parts.add(rp)
                        matched_pairs.append({
                            "left_part_number": left_part,
                            "right_part_number": rp,
                            "reason": "suffix_based",
                        })
                        matched = True
                        break

            if not matched:
                missing_in_right.append(left_part)

        extra_in_right = sorted([p for p in right_parts if p not in used_right_parts])

        # --- Qty mismatches ---
        qty_mismatches_raw = []
        for pair in matched_pairs:
            left_part = pair["left_part_number"]
            right_part = pair["right_part_number"]
            left_qty = self._get_total_quantity(left_df, left_part)
            right_qty = self._get_total_quantity(right_df, right_part)
            if left_qty != right_qty:
                qty_mismatches_raw.append({
                    "left_part_number": left_part,
                    "right_part_number": right_part,
                    "left_quantity": left_qty,
                    "right_quantity": right_qty,
                    "reason": pair["reason"],
                })

        qty_mismatches = self._dedup_qty_mismatches(qty_mismatches_raw)
        reason_summary = self._build_reason_summary(matched_pairs)
        kpi_cards = self._build_kpi_cards(
            matched_pairs=matched_pairs,
            qty_mismatches=qty_mismatches,
            missing_in_right=missing_in_right,
            extra_in_right=extra_in_right,
            reason_summary=reason_summary,
        )

        return {
            "missing_in_right": sorted(missing_in_right),
            "extra_in_right": extra_in_right,
            "qty_mismatches": qty_mismatches,
            "matched_pairs": matched_pairs,
            "reason_summary": reason_summary,
            "kpi_cards": kpi_cards,
        }

    def _build_deleted_set(self, df: pd.DataFrame) -> set:
        """ساخت set از شماره قطعات deleted - O(n) یک بار"""
        deleted = set()
        if "part_number" not in df.columns or "description" not in df.columns:
            return deleted
        mask = df["description"].fillna("").astype(str).str.strip().str.lower() == "deleted"
        deleted_rows = df[mask]["part_number"].dropna().astype(str).str.strip()
        return set(deleted_rows)

    def _dedup_qty_mismatches(self, mismatches: list[dict]) -> list[dict]:
        reason_rank = {"exact": 1, "alternative_part": 2, "sap_mpn": 3, "suffix_based": 4}
        best_by_pair = {}
        for row in mismatches:
            key = (row["left_part_number"], row["right_part_number"])
            current_rank = reason_rank.get(row.get("reason"), 999)
            if key not in best_by_pair:
                best_by_pair[key] = row
                continue
            existing_rank = reason_rank.get(best_by_pair[key].get("reason"), 999)
            if current_rank < existing_rank:
                best_by_pair[key] = row
        return sorted(
            best_by_pair.values(),
            key=lambda x: (str(x["left_part_number"]), str(x["right_part_number"])),
        )

    def _build_reason_summary(self, matched_pairs: list[dict]) -> list[dict]:
        total = len(matched_pairs)
        reason_order = ["exact", "alternative_part", "sap_mpn", "suffix_based"]
        counts = {r: 0 for r in reason_order}
        for row in matched_pairs:
            r = row.get("reason", "unknown")
            counts[r] = counts.get(r, 0) + 1
        summary = []
        for r in reason_order + [k for k in counts.keys() if k not in reason_order]:
            c = counts.get(r, 0)
            pct = (c / total * 100.0) if total > 0 else 0.0
            summary.append({"reason": r, "count": c, "percentage": round(pct, 2)})
        return summary

    def _build_kpi_cards(self, matched_pairs, qty_mismatches, missing_in_right, extra_in_right, reason_summary) -> dict:
        total_matched = len(matched_pairs)
        total_qty_mismatch = len(qty_mismatches)
        total_missing = len(missing_in_right)
        total_extra = len(extra_in_right)

        def reason_count(name):
            for row in reason_summary:
                if row["reason"] == name:
                    return int(row["count"])
            return 0

        exact_count = reason_count("exact")
        alt_count = reason_count("alternative_part")
        mpn_count = reason_count("sap_mpn")
        suffix_count = reason_count("suffix_based")
        exact_pct = round((exact_count / total_matched * 100.0), 2) if total_matched else 0.0
        alt_pct = round((alt_count / total_matched * 100.0), 2) if total_matched else 0.0
        mpn_pct = round((mpn_count / total_matched * 100.0), 2) if total_matched else 0.0
        suffix_pct = round((suffix_count / total_matched * 100.0), 2) if total_matched else 0.0
        qty_match_rate = round(((total_matched - total_qty_mismatch) / total_matched * 100.0), 2) if total_matched else 0.0

        return {
            "total_matched": total_matched,
            "qty_mismatches": total_qty_mismatch,
            "missing_in_right": total_missing,
            "extra_in_right": total_extra,
            "exact_count": exact_count,
            "alternative_count": alt_count,
            "sap_mpn_count": mpn_count,
            "suffix_count": suffix_count,
            "exact_pct": exact_pct,
            "alternative_pct": alt_pct,
            "sap_mpn_pct": mpn_pct,
            "suffix_pct": suffix_pct,
            "qty_match_rate_pct": qty_match_rate,
        }

    def _get_total_quantity(self, df: pd.DataFrame, part_number: str):
        filtered = df[df["part_number"].astype(str).str.strip() == str(part_number).strip()]
        if "quantity" not in filtered.columns:
            return None
        total = pd.to_numeric(filtered["quantity"], errors="coerce").fillna(0).sum()
        if pd.isna(total):
            return 0
        if float(total).is_integer():
            return int(total)
        return float(total)

    # --- Legacy methods (backward compat) ---
    def _find_equivalent_part_with_reason(self, source_part, candidate_parts, source_df, candidate_df):
        priority_rank = {"exact": 1, "alternative_part": 2, "suffix_based": 3}
        best_match = None
        best_rank = 999
        for candidate in candidate_parts:
            result = self.resolver.get_equivalence_result(source_part, candidate, left_df=source_df, right_df=candidate_df)
            if not result["is_equivalent"]:
                continue
            reason = result["reason"]
            rank = priority_rank.get(reason, 999)
            if rank < best_rank:
                best_rank = rank
                best_match = {"candidate": candidate, "reason": reason}
            if best_rank == 1:
                break
        return best_match
