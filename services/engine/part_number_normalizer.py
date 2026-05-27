from typing import Optional, List
import re


class PartNumberNormalizer:
    """
    Normalizes part numbers for consistent comparison.
    Handles common variations like dashes, spaces, case, and suffixes.
    """

    @staticmethod
    def normalize(part_num: str) -> str:
        """
        Normalize a part number by removing non-alphanumeric characters,
        converting to uppercase, and standardizing common patterns.

        Args:
            part_num: Raw part number string

        Returns:
            Normalized part number string
        """
        if not isinstance(part_num, str):
            return ""

        # Convert to string and strip whitespace
        part_num = str(part_num).strip()
        if not part_num:
            return ""

        # Remove all non-alphanumeric characters except underscores
        # Keep underscores as they often separate meaningful segments
        cleaned = re.sub(r'[^a-zA-Z0-9_]', '', part_num)

        # Handle common suffixes that may vary (e.g., -R1, -REV2, /A, /B)
        # Remove revision indicators at the end
        cleaned = re.sub(r'(?:[-_/][rR][eE][vV]\d+|[-_/][rR]\d+|[-_/][a-zA-Z]\d*|[-_/]\d+)$', '', cleaned)

        # Normalize multiple underscores to single underscore
        cleaned = re.sub(r'_+', '_', cleaned)

        # Remove leading/trailing underscores
        cleaned = cleaned.strip('_')

        return cleaned.upper()

    @staticmethod
    def normalize_fuzzy(part_num: str) -> str:
        """
        Fuzzy normalization for cases where exact matching fails.
        Removes all separators and digits after letters.

        Args:
            part_num: Raw part number string

        Returns:
            Fuzzy-normalized part number string
        """
        if not isinstance(part_num, str):
            return ""

        part_num = str(part_num).strip()
        if not part_num:
            return ""

        # Remove all non-alphanumeric characters
        cleaned = re.sub(r'[^a-zA-Z0-9]', '', part_num)

        # Remove trailing digits (common in variants)
        cleaned = re.sub(r'\d+$', '', cleaned)

        return cleaned.upper()

    @staticmethod
    def get_all_variants(part_num: str) -> List[str]:
        """
        Generate common variants of a part number for broader matching.

        Args:
            part_num: Raw part number string

        Returns:
            List of normalized variants
        """
        if not isinstance(part_num, str):
            return []

        base = PartNumberNormalizer.normalize(part_num)
        fuzzy = PartNumberNormalizer.normalize_fuzzy(part_num)

        variants = [base]
        if fuzzy and fuzzy != base:
            variants.append(fuzzy)

        # Add base without last segment (for multi-segment part numbers)
        if '_' in base:
            truncated = '_'.join(base.split('_')[:-1])
            if truncated and truncated != base:
                variants.append(truncated)

        return list(set(variants))  # Remove duplicates


# Example usage and basic test
if __name__ == "__main__":
    # Test cases
    test_cases = [
        "12345-REV1",
        "ABC-123-R2",
        "XYZ_456/A",
        "789-012-345",
        "DEF 789",
        "GHI-789-01",
    ]

    print("Part Number Normalization Examples:")
    for case in test_cases:
        norm = PartNumberNormalizer.normalize(case)
        fuzzy = PartNumberNormalizer.normalize_fuzzy(case)
        variants = PartNumberNormalizer.get_all_variants(case)
        print(f"{case:15} -> norm: {norm:15}, fuzzy: {fuzzy:15}, variants: {variants}")
