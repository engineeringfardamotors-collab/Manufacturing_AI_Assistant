# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

# add project root to path
CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.engine.comparator import Comparator, CompareConfig


def _write_excel(path: Path, df: pd.DataFrame, sheet_name: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=False)


def test_read_balance_detects_fa_main_and_alt_headers(tmp_path: Path):
    """
    باید اتوماتیک:
      - 'شماره فنی' => main_part_no
      - 'شماره فنی جایگزین' => alt_part_no
    را تشخیص بدهد.
    """
    df = pd.DataFrame(
        {
            "ردیف": [1, 2],
            "شماره فنی": ["aa-001", "bb-002"],
            "شماره فنی جایگزین": ["aa-001-alt", ""],
            "شرح": ["قطعه A", "قطعه B"],
            "ضریب مصرف": [1.0, 2.5],
        }
    )

    fpath = tmp_path / "balance_fa.xlsx"
    _write_excel(fpath, df, sheet_name="Sheet1")

    comp = Comparator(CompareConfig())
    out = comp.read_balance_fixed_index(str(fpath), sheet_name="Sheet1")

    assert list(out.columns) == ["main_part_no", "alt_part_no", "part_desc", "consumption_ratio"]
    assert len(out) == 2

    assert out.iloc[0]["main_part_no"] == "AA-001"
    assert out.iloc[0]["alt_part_no"] == "AA-001-ALT"
    assert out.iloc[1]["main_part_no"] == "BB-002"

    assert float(out.iloc[0]["consumption_ratio"]) == 1.0
    assert float(out.iloc[1]["consumption_ratio"]) == 2.5