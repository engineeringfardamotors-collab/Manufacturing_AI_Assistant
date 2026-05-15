import sys
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[1]))

from services.engine.comparator import DatasetComparator


def run_smoke_test():
    left_df = pd.DataFrame(
        {
            "part_number": ["10879833", "11111111", "22222222"],
            "description": ["PART A", "PART B", "PART C"],
            "quantity": [1, 2, 3],
        }
    )

    right_df = pd.DataFrame(
        {
            "part_number": ["10879833", "11111111", "33333333"],
            "description": ["PART A", "PART B", "PART D"],
            "quantity": [1, 5, 4],
        }
    )

    comparator = DatasetComparator()
    result = comparator.compare(left_df, right_df)

    print(result)


if __name__ == "__main__":
    run_smoke_test()