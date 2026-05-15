import sys
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[1]))

from services.engine.mapping_engine import MappingEngine
from services.engine.normalizer import DataNormalizer


def run_smoke_test():
    df = pd.DataFrame(
        {
            "Internal Material No": ["10879833", "10879833-L01"],
            "Description": ["PART A", "PART A ALT"],
            "Qty": [1, 2],
            "Alternative Part": ["", "10879833"],
            "Other Column": ["x", "y"],
        }
    )

    mapping_engine = MappingEngine()
    detected = mapping_engine.detect_columns(df.columns)

    normalizer = DataNormalizer()
    normalized_df = normalizer.normalize_dataframe(df, detected)

    print(normalized_df)
    print(list(normalized_df.columns))


if __name__ == "__main__":
    run_smoke_test()