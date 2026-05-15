import sys
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[1]))

from services.engine.alternative_resolver import AlternativePartResolver


def run_smoke_test():
    df = pd.DataFrame(
        {
            "part_number": ["10879833-L01", "99999999"],
            "alternative_part": ["10879833", ""],
        }
    )

    resolver = AlternativePartResolver()

    print("exact:", resolver.are_equivalent("10879833", "10879833", df, df))
    print("alternative_col:", resolver.are_equivalent("10879833-L01", "10879833", df, df))
    print("suffix_base:", resolver.are_equivalent("10879833-L02", "10879833", None, None))
    print("suffix_suffix_same_base:", resolver.are_equivalent("10879833-L01", "10879833-L03", None, None))
    print("not_equivalent:", resolver.are_equivalent("99999999", "10879833", df, df))


if __name__ == "__main__":
    run_smoke_test()