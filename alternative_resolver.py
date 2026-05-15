import re
import pandas as pd


class AlternativePartResolver:
    SUFFIX_PATTERN = re.compile(r"^(?P<base>.+)-L\d{2}$", re.IGNORECASE)

    def are_equivalent(
        self,
        left_part: str,
        right_part: str,
        left_df: pd.DataFrame | None = None,
        right_df: pd.DataFrame | None = None,
    ) -> bool:
        result = self.get_equivalence_result(left_part, right_part, left_df, right_df)
        return result["is_equivalent"]

    def get_equivalence_result(
        self,
        left_part: str,
        right_part: str,
        left_df: pd.DataFrame | None = None,
        right_df: pd.DataFrame | None = None,
    ) -> dict:
        left_part = self._normalize_part(left_part)
        right_part = self._normalize_part(right_part)

        if not left_part or not right_part:
            return {"is_equivalent": False, "reason": "invalid_input"}

        if self.is_deleted_part(left_part, left_df) or self.is_deleted_part(right_part, right_df):
            return {"is_equivalent": False, "reason": "deleted"}

        # Priority 1: exact
        if left_part == right_part:
            return {"is_equivalent": True, "reason": "exact"}

        # Priority 2: alternative_part (base-aware)
        if left_df is not None and self._is_alternative_relation_base_aware(left_df, left_part, right_part):
            return {"is_equivalent": True, "reason": "alternative_part"}

        if right_df is not None and self._is_alternative_relation_base_aware(right_df, right_part, left_part):
            return {"is_equivalent": True, "reason": "alternative_part"}

        # Priority 3: suffix_based
        if self._is_suffix_equivalent(left_part, right_part):
            return {"is_equivalent": True, "reason": "suffix_based"}

        return {"is_equivalent": False, "reason": "not_equivalent"}

    def is_deleted_part(self, part_number: str, df: pd.DataFrame | None) -> bool:
        if df is None:
            return False
        if "part_number" not in df.columns or "description" not in df.columns:
            return False

        temp_df = df.copy()
        temp_df["part_number"] = temp_df["part_number"].astype(str).str.strip()
        temp_df["description"] = temp_df["description"].fillna("").astype(str).str.strip().str.lower()

        rows = temp_df[temp_df["part_number"] == self._normalize_part(part_number)]
        if rows.empty:
            return False

        return any(rows["description"] == "deleted")

    def _is_alternative_relation_base_aware(self, df: pd.DataFrame, source_part: str, target_part: str) -> bool:
        if "part_number" not in df.columns or "alternative_part" not in df.columns:
            return False

        temp_df = df.copy()
        temp_df["part_number"] = temp_df["part_number"].astype(str).str.strip()
        temp_df["alternative_part"] = temp_df["alternative_part"].fillna("").astype(str).str.strip()

        # Update candidate forms to include MPN lookup
        def _extend_with_mpn_lookup(part, mpn_to_internal, internal_to_mpns):
            candidates = {part}
            if part in mpn_to_internal:
                candidates.add(mpn_to_internal[part])
            if part in internal_to_mpns:
                candidates.update(internal_to_mpns[part])
            return candidates

        source_candidates = self._candidate_forms(source_part)
        target_candidates = self._candidate_forms(target_part)

        if "mpn_lookup" in st.session_state:
            mpn_lookup = st.session_state.mpn_lookup
            mpn_to_internal = mpn_lookup.get("mpn_to_internal", {})
            internal_to_mpns = mpn_lookup.get("internal_to_mpns", {})

            source_candidates = _extend_with_mpn_lookup(source_part, mpn_to_internal, internal_to_mpns)
            target_candidates = _extend_with_mpn_lookup(target_part, mpn_to_internal, internal_to_mpns)

        matched_rows = temp_df[temp_df["part_number"].isin(source_candidates)]
        if matched_rows.empty:
            return False

        alternatives = set(matched_rows["alternative_part"].dropna().astype(str).str.strip())
        return any(t in alternatives for t in target_candidates)

    def _candidate_forms(self, part_number: str) -> set[str]:
        part_number = self._normalize_part(part_number)
        candidates = {part_number}
        base = self._extract_base_if_suffix(part_number)
        if base:
            candidates.add(base)
        return candidates

    def _is_suffix_equivalent(self, part_a: str, part_b: str) -> bool:
        base_a = self._extract_base_if_suffix(part_a)
        base_b = self._extract_base_if_suffix(part_b)

        if base_a and base_a == part_b:
            return True
        if base_b and base_b == part_a:
            return True
        if base_a and base_b and base_a == base_b:
            return True

        return False

    def _extract_base_if_suffix(self, part_number: str) -> str | None:
        match = self.SUFFIX_PATTERN.match(part_number)
        if not match:
            return None
        return match.group("base").strip()

    def _normalize_part(self, value: str) -> str:
        if value is None:
            return ""
        return str(value).strip()