import sys
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[1]))

from services.engine.comparator import DatasetComparator


def run_smoke_test():
    left_df = pd.DataFrame(
        {
            "part_number": ["10879833", "22222222", "77777777"],
            "description": ["PART A", "PART C", "deleted"],
            "quantity": [1, 3, 9],
            "alternative_part": ["", "", ""],
        }
    )

    right_df = pd.DataFrame(
        {
            "part_number": ["10879833-L02", "33333333", "88888888"],
            "description": ["PART A ALT", "PART D", "deleted"],
            "quantity": [1, 4, 10],
            "alternative_part": ["10879833", "", ""],
        }
    )

    comparator = DatasetComparator()
    result = comparator.compare(left_df, right_df)

    print(result)


if __name__ == "__main__":
    run_smoke_test()