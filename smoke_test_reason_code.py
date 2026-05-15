import sys
from pathlib import Path

import pandas as pd

# --- Fix import path for "services" package ---
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.engine.comparator import DatasetComparator


def main():
    # Left dataset (مثلاً Packing)
    left_df = pd.DataFrame(
        [
            {
                "part_number": "10879833",
                "quantity": 2,
                "alternative_part": "",
                "description": "Main Part",
            },
            {
                "part_number": "10879833-L03",
                "quantity": 3,
                "alternative_part": "10879833-L01",
                "description": "Alt Part L03",
            },
            {
                "part_number": "AAA",
                "quantity": 1,
                "alternative_part": "",
                "description": "Normal Part",
            },
        ]
    )

    # Right dataset (مثلاً Balance/BOM)
    right_df = pd.DataFrame(
        [
            {
                "part_number": "10879833",
                "quantity": 3,
                "alternative_part": "",
                "description": "Main Part",
            },
            {
                "part_number": "10879833-L01",
                "quantity": 2,
                "alternative_part": "",
                "description": "Alt Part L01",
            },
            {
                "part_number": "AAA",
                "quantity": 1,
                "alternative_part": "",
                "description": "Normal Part",
            },
        ]
    )

    comparator = DatasetComparator()
    comparison_result = comparator.compare(left_df, right_df)

    print("matched_pairs:")
    for row in comparison_result["matched_pairs"]:
        print(row)

    print("\nqty_mismatches:")
    for row in comparison_result["qty_mismatches"]:
        print(row)

    print("\nmissing_in_right:", comparison_result["missing_in_right"])
    print("extra_in_right:", comparison_result["extra_in_right"])

    print("\nreason_summary:")
    for row in comparison_result["reason_summary"]:
        print(row)

    print("\nkpi_cards:")
    print(comparison_result["kpi_cards"])


if __name__ == "__main__":
    main()