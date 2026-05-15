import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from services.engine.mapping_engine import MappingEngine


def run_smoke_test():
    sample_columns = [
        "Internal Material No",
        "Description",
        "Qty",
        "Alternative Part",
    ]

    engine = MappingEngine()
    detected = engine.detect_columns(sample_columns)

    print(detected)


if __name__ == "__main__":
    run_smoke_test()
