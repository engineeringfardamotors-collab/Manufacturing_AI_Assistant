import sys
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[1]))

from services.engine.mapping_orchestrator import MappingOrchestrator


def run_smoke_test():
    df = pd.DataFrame(
        {
            "Internal Material No": ["10879833", "10879833-L01"],
            "Description": ["PART A", "PART A ALT"],
            "Qty": [1, 2],
            "Alternative Part": ["", "10879833"],
            "MPN Number": ["10879833", "10879833"],
            "Other Column": ["x", "y"],
        }
    )

    orchestrator = MappingOrchestrator()
    result = orchestrator.process(df)

    print("file_type:", result["file_type"])
    print("scores:", result["file_type_scores"])
    print("detected_columns:", result["detected_columns"])
    print(result["normalized_df"])


if __name__ == "__main__":
    run_smoke_test()