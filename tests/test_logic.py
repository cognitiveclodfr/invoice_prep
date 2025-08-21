import pytest
import pandas as pd
import os
from src.app.calculator_logic import calculate_costs

@pytest.fixture
def create_test_csv(tmp_path):
    """Creates a temporary CSV file for testing."""
    csv_content = """Name,Fulfillment Status,Lineitem quantity,Lineitem sku,Lineitem name,Fulfilled at
#1,fulfilled,2,SKU-A,Product A,2025-07-15 10:00:00
#2,fulfilled,1,SKU-B,Product B,2025-08-01 11:00:00
#2,fulfilled,2,SKU-C,Product C,2025-08-01 11:00:00
#3,fulfilled,1,SKU-D,Product D,2025-07-01 12:00:00
#3,fulfilled,4,VIRTUAL-01,Virtual Product 1,2025-07-01 12:00:00
#4,unfulfilled,5,SKU-E,Product E,2025-07-16 13:00:00
#5,fulfilled,3,SKU-F,Product F,2025-06-30 14:00:00
"""
    csv_path = tmp_path / "test_data.csv"
    csv_path.write_text(csv_content)
    return str(csv_path)

# Test case 1: Baseline successful calculation
def test_successful_calculation(create_test_csv):
    results = calculate_costs(
        filepath=create_test_csv,
        first_sku_cost=10, next_sku_cost=5, unit_cost=2,
        start_date_str="2025-07-01", end_date_str="2025-07-31"
    )
    assert results['error'] is None
    assert results['totals']['processed_orders_count'] == 2
    assert results['totals']['total_units'] == 7 # 2 from #1, 5 from #3
    # Corrected expected values. Order #1 (1 sku, 2 units) = 1*10 + 2*2 = 14. Order #3 (2 skus, 5 units) = 1*10 + 1*5 + 5*2 = 25. Total = 39.
    assert results['totals']['total_cost_bgn'] == 39.00
    assert len(results['line_item_df']) == 3 # A, D, VIRTUAL-01

# Test case 2: SKU exclusion
def test_sku_exclusion(create_test_csv):
    results = calculate_costs(
        filepath=create_test_csv,
        first_sku_cost=10, next_sku_cost=5, unit_cost=2,
        start_date_str="2025-07-01", end_date_str="2025-07-31",
        excluded_skus=["VIRTUAL-01"]
    )
    assert results['error'] is None
    assert results['totals']['processed_orders_count'] == 2
    assert results['totals']['total_units'] == 3 # 2 from #1, 1 from #3 (VIRTUAL-01 is excluded)
    assert results['totals']['total_cost_bgn'] == 26.00 # Order #1=14. Order #3 (now 1 sku, 1 unit) = 1*10 + 1*2 = 12. Total = 26.
    assert len(results['line_item_df']) == 2 # A, D

# Test case 3: Missing column
def test_missing_column(tmp_path):
    csv_content = "Name,Fulfillment Status\n#1,fulfilled"
    csv_path = tmp_path / "bad_data.csv"
    csv_path.write_text(csv_content)
    results = calculate_costs(str(csv_path), 10, 5, 2)
    assert 'Missing required column' in results['error']

# Test case 4: Empty file
def test_empty_file(tmp_path):
    csv_path = tmp_path / "empty.csv"
    csv_path.touch()
    results = calculate_costs(str(csv_path), 10, 5, 2)
    # This might raise an exception in pandas read_csv, which is caught
    assert results['error'] is not None

# Test case 5: No fulfilled orders
def test_no_fulfilled_orders(tmp_path):
    csv_content = """Name,Fulfillment Status,Lineitem quantity,Lineitem sku,Lineitem name,Fulfilled at
#4,unfulfilled,5,SKU-E,Product E,2025-07-16 13:00:00
"""
    csv_path = tmp_path / "no_fulfilled.csv"
    csv_path.write_text(csv_content)
    results = calculate_costs(str(csv_path), 10, 5, 2)
    assert results['error'] is None
    assert results['totals']['processed_orders_count'] == 0
