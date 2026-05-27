from typing import List, Dict, Optional
import re


class AlternativeResolver:
    """
    Resolves alternative part numbers using configurable rules and patterns.
    """

    def __init__(self):
        # Common pattern mappings for known variants
        self.pattern_mappings = [
            # Replace common prefixes/suffixes
            (r'^P-', 'P'),
            (r'^PART-', 'P'),
            (r'^ITEM-', 'I'),
            (r'-[A-Z]{1,2}$', ''),  # Remove single/double letter suffixes
            (r'[-_](?:REV|REVISION|VERSION)\d*', ''),  # Remove revision indicators
        ]

    def resolve_alternatives(self, part_num: str) -> List[str]:
        """
        Generate alternative part numbers based on common patterns.

        Args:
            part_num: Original part number

        Returns:
            List of alternative part numbers
        """
        if not isinstance(part_num, str):
            return []

        alternatives = [part_num.strip()]

        # Apply pattern mappings
        for pattern, replacement in self.pattern_mappings:
            modified = re.sub(pattern, replacement, part_num)
            if modified != part_num and modified.strip():
                alternatives.append(modified.strip())

        # Add numeric-only variant if part number contains digits
        if re.search(r'\d', part_num):
            numeric_only = re.sub(r'[^0-9]', '', part_num)
            if numeric_only and numeric_only != part_num:
                alternatives.append(numeric_only)

        # Add alphanumeric-only variant
        alpha_numeric = re.sub(r'[^a-zA-Z0-9]', '', part_num)
        if alpha_numeric and alpha_numeric != part_num:
            alternatives.append(alpha_numeric)

        # Remove duplicates while preserving order
        seen = set()
        unique_alternatives = []
        for alt in alternatives:
            if alt not in seen:
                seen.add(alt)
                unique_alternatives.append(alt)

        return unique_alternatives

    def is_variant_of(self, candidate: str, base: str) -> bool:
        """
        Check if candidate is likely a variant of base part number.

        Args:
            candidate: Candidate part number to check
            base: Base part number

        Returns:
            True if candidate appears to be a variant of base
        """
        if not isinstance(candidate, str) or not isinstance(base, str):
            return False

        candidate_clean = re.sub(r'[^a-zA-Z0-9]', '', candidate.upper())
        base_clean = re.sub(r'[^a-zA-Z0-9]', '', base.upper())

        # Exact match after cleaning
        if candidate_clean == base_clean:
            return True

        # Startswith match (candidate is longer version)
        if candidate_clean.startswith(base_clean) and len(candidate_clean) > len(base_clean):
            return True

        # Endswith match (base is longer version)
        if base_clean.startswith(candidate_clean) and len(base_clean) > len(candidate_clean):
            return True

        return False


# Example usage and basic test
if __name__ == "__main__":
    resolver = AlternativeResolver()
    test_part = "P-12345-REV2"
    alternatives = resolver.resolve_alternatives(test_part)
    print(f"Alternatives for {test_part}: {alternatives}")

    # Test variant checking
    print(f"Is '12345' a variant of '{test_part}'? {resolver.is_variant_of('12345', test_part)}")
    print(f"Is 'P12345' a variant of '{test_part}'? {resolver.is_variant_of('P12345', test_part)}")
