import pytest
import pandas as pd
from services.engine.comparator import Comparator


def test_comparator_basic_matching():
    """Test basic part number matching with normalization."""
    comparator = Comparator()
    
    # Test data
    packing_df = pd.DataFrame([
        {'Part Number': '12345-REV1', 'Qty': 10},
        {'Part Number': 'ABC-678-R2', 'Qty': 5},
        {'Part Number': 'XYZ_999/A', 'Qty': 2},
    ])
    
    balance_df = pd.DataFrame([
        {'Part Number': '12345', 'Qty': 10},
        {'Part Number': 'ABC678', 'Qty': 5},
        {'Part Number': 'XYZ999', 'Qty': 2},
        {'Part Number': 'DEF000', 'Qty': 1},
    ])

    result = comparator.compare_parts(packing_df, balance_df)
    
    assert result['summary']['matched'] == 3
    assert len(result['packing_only']) == 0
    assert len(result['balance_only']) == 1


def test_comparator_variant_matching():
    """Test variant-based matching when exact normalization fails."""
    comparator = Comparator()
    
    # Test data where normalization alone won't match
    packing_df = pd.DataFrame([
        {'Part Number': 'P-12345', 'Qty': 10},
        {'Part Number': 'ITEM-678', 'Qty': 5},
    ])
    
    balance_df = pd.DataFrame([
        {'Part Number': '12345', 'Qty': 10},
        {'Part Number': '678', 'Qty': 5},
    ])

    result = comparator.compare_parts(packing_df, balance_df)
    
    assert result['summary']['matched'] == 2


def test_comparator_empty_inputs():
    """Test behavior with empty DataFrames."""
    comparator = Comparator()
    
    empty_df = pd.DataFrame()
    packing_df = pd.DataFrame([{'Part Number': '123', 'Qty': 1}])
    
    # Empty packing list
    result = comparator.compare_parts(empty_df, packing_df)
    assert result['summary']['matched'] == 0
    
    # Empty balance
    result = comparator.compare_parts(packing_df, empty_df)
    assert result['summary']['matched'] == 0


def test_comparator_no_matches():
    """Test behavior when no matches are found."""
    comparator = Comparator()
    
    packing_df = pd.DataFrame([
        {'Part Number': '123', 'Qty': 1},
        {'Part Number': '456', 'Qty': 1},
    ])
    
    balance_df = pd.DataFrame([
        {'Part Number': '789', 'Qty': 1},
        {'Part Number': '012', 'Qty': 1},
    ])

    result = comparator.compare_parts(packing_df, balance_df)
    
    assert result['summary']['matched'] == 0
    assert len(result['packing_only']) == 2
    assert len(result['balance_only']) == 2
