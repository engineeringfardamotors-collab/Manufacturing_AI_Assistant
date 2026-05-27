from typing import Dict, Any, List, Set
import re
import pandas as pd


class Comparator:
    def __init__(self):
        pass

    def _norm(self, value: Any) -> str:
        s = str(value or "").strip().upper()
        if not s:
            return ""
        # remove separators
        s = re.sub(r"[\s\-_\/\.]+", "", s)

        # remove common revision suffixes at end: REV1, R2, A, B ...
        s = re.sub(r"(REV\d+|R\d+)$", "", s)

        # if ends with single letter after digits (e.g. XYZ999A) remove that letter
        s = re.sub(r"(?<=\d)[A-Z]$", "", s)

        return s

    def _variants(self, part: Any) -> Set[str]:
        raw = str(part or "").strip().upper()
        out: Set[str] = set()

        n = self._norm(raw)
        if n:
            out.add(n)

        # prefix-stripping variants for cases like P-12345 / ITEM-678
        m = re.match(r"^(P|ITEM|ITM|PART)[\-_ ]*(.+)$", raw)
        if m:
            out.add(self._norm(m.group(2)))

        # digits-only variant
        digits = re.sub(r"\D+", "", raw)
        if digits:
            out.add(digits)

        out.discard("")
        return out

    def compare_parts(
        self,
        packing_list_df: pd.DataFrame,
        balance_df: pd.DataFrame,
        packing_part_col: str = "Part Number",
        balance_part_col: str = "Part Number",
    ) -> Dict[str, Any]:
        packing_rows = packing_list_df.to_dict("records") if not packing_list_df.empty else []
        balance_rows = balance_df.to_dict("records") if not balance_df.empty else []

        used_p: Set[int] = set()
        used_b: Set[int] = set()
        matched_rows: List[Dict[str, Any]] = []

        # Step 1: exact normalized one-to-one
        b_map: Dict[str, List[int]] = {}
        for bi, b in enumerate(balance_rows):
            bn = self._norm(b.get(balance_part_col, ""))
            b_map.setdefault(bn, []).append(bi)

        for pi, p in enumerate(packing_rows):
            pn = self._norm(p.get(packing_part_col, ""))
            for bi in b_map.get(pn, []):
                if bi in used_b:
                    continue
                matched_rows.append(
                    {"packing": p, "balance": balance_rows[bi], "match_type": "exact_normalized"}
                )
                used_p.add(pi)
                used_b.add(bi)
                break

        # Step 2: variant-based one-to-one
        for pi, p in enumerate(packing_rows):
            if pi in used_p:
                continue
            pv = self._variants(p.get(packing_part_col, ""))

            for bi, b in enumerate(balance_rows):
                if bi in used_b:
                    continue
                bv = self._variants(b.get(balance_part_col, ""))
                if pv.intersection(bv):
                    matched_rows.append(
                        {"packing": p, "balance": b, "match_type": "alternative"}
                    )
                    used_p.add(pi)
                    used_b.add(bi)
                    break

        packing_only = [r for i, r in enumerate(packing_rows) if i not in used_p]
        balance_only = [r for i, r in enumerate(balance_rows) if i not in used_b]

        summary = {
            "matched": len(matched_rows),
            "packing_only": len(packing_only),
            "balance_only": len(balance_only),
            "total_packing": len(packing_rows),
            "total_balance": len(balance_rows),
        }

        return {
            "matched_rows": matched_rows,
            "packing_only": packing_only,
            "balance_only": balance_only,
            "summary": summary,
        }