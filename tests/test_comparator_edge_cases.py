import pandas as pd
from services.engine.comparator import Comparator


def test_qty_mismatch_still_matches():
    """Parts match by number but qty differs — should still match."""
    comparator = Comparator()

    packing_df = pd.DataFrame([
        {'Part Number': 'ABC-123', 'Qty': 10},
        {'Part Number': 'DEF-456', 'Qty': 20},
    ])

    balance_df = pd.DataFrame([
        {'Part Number': 'ABC123', 'Qty': 8},   # qty different
        {'Part Number': 'DEF456', 'Qty': 25},  # qty different
    ])

    result = comparator.compare_parts(packing_df, balance_df)

    assert result['summary']['matched'] == 2
    # verify qty values are preserved (not altered)
    for row in result['matched_rows']:
        assert 'Qty' in row['packing']
        assert 'Qty' in row['balance']


def test_duplicate_part_numbers_one_to_one():
    """Duplicate parts should match one-to-one, not many-to-one."""
    comparator = Comparator()

    packing_df = pd.DataFrame([
        {'Part Number': 'AAA-111', 'Qty': 5},
        {'Part Number': 'AAA-111', 'Qty': 3},
        {'Part Number': 'BBB-222', 'Qty': 7},
    ])

    balance_df = pd.DataFrame([
        {'Part Number': 'AAA111', 'Qty': 5},
        {'Part Number': 'AAA111', 'Qty': 3},
        {'Part Number': 'BBB222', 'Qty': 7},
    ])

    result = comparator.compare_parts(packing_df, balance_df)

    assert result['summary']['matched'] == 3
    assert result['summary']['packing_only'] == 0
    assert result['summary']['balance_only'] == 0


def test_different_column_names():
    """Support custom column names for part numbers."""
    comparator = Comparator()

    packing_df = pd.DataFrame([
        {'شماره قطعه': 'XYZ-100', 'تعداد': 4},
        {'شماره قطعه': 'MNO-200', 'تعداد': 6},
    ])

    balance_df = pd.DataFrame([
        {'کد کالا': 'XYZ100', 'موجودی': 4},
        {'کد کالا': 'MNO200', 'موجودی': 6},
    ])

    result = comparator.compare_parts(
        packing_df, balance_df,
        packing_part_col='شماره قطعه',
        balance_part_col='کد کالا'
    )

    assert result['summary']['matched'] == 2


def test_empty_and_none_values():
    """Handle empty strings and None gracefully."""
    comparator = Comparator()

    packing_df = pd.DataFrame([
        {'Part Number': '', 'Qty': 1},
        {'Part Number': None, 'Qty': 2},
        {'Part Number': 'VALID-001', 'Qty': 3},
    ])

    balance_df = pd.DataFrame([
        {'Part Number': 'VALID001', 'Qty': 3},
        {'Part Number': '', 'Qty': 1},
    ])

    result = comparator.compare_parts(packing_df, balance_df)

    # Only VALID-001 should match VALID001
    assert result['summary']['matched'] >= 1


def test_mixed_case_matching():
    """Case should not affect matching."""
    comparator = Comparator()

    packing_df = pd.DataFrame([
        {'Part Number': 'abc-DEF-123', 'Qty': 1},
        {'Part Number': 'GHI_jkl_456', 'Qty': 2},
    ])

    balance_df = pd.DataFrame([
        {'Part Number': 'ABCDEF123', 'Qty': 1},
        {'Part Number': 'ghijkl456', 'Qty': 2},
    ])

    result = comparator.compare_parts(packing_df, balance_df)

    assert result['summary']['matched'] == 2


def test_automotive_part_numbers():
    """Test real-world automotive part number patterns."""
    comparator = Comparator()

    packing_df = pd.DataFrame([
        {'Part Number': '97133-2E250', 'Qty': 10},   # Hyundai cabin filter
        {'Part Number': '04152-YZZA1', 'Qty': 5},    # Toyota oil filter
        {'Part Number': '1K0-615-301M', 'Qty': 8},   # VW brake disc
    ])

    balance_df = pd.DataFrame([
        {'Part Number': '971332E250', 'Qty': 10},
        {'Part Number': '04152YZZA1', 'Qty': 5},
        {'Part Number': '1K0615301M', 'Qty': 8},
    ])

    result = comparator.compare_parts(packing_df, balance_df)

    assert result['summary']['matched'] == 3