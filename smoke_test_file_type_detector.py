import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from services.engine.file_type_detector import FileTypeDetector


def run_smoke_test():
    detector = FileTypeDetector()

    sample_columns = [
        "Internal Material No",
        "Description",
        "Qty",
        "Alternative Part",
        "MPN Number",
    ]

    result = detector.detect(sample_columns)
    print(result)


if __name__ == "__main__":
    run_smoke_test()