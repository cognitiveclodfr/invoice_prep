import pytest
import pandas as pd
import os
from src.app.calculator_logic import calculate_costs

@pytest.fixture
def create_test_csv(tmp_path):
    """Creates a temporary CSV file for testing."""
    # This CSV now includes an order (#6) with items split across the date boundary
    csv_content = """Name,Fulfillment Status,Lineitem quantity,Lineitem sku,Lineitem name,Fulfilled at
#1,fulfilled,2,SKU-A,Product A,2025-07-15 10:00:00
#2,fulfilled,1,SKU-B,Product B,2025-08-01 11:00:00
#3,fulfilled,1,SKU-D,Product D,2025-07-01 12:00:00
#3,fulfilled,4,VIRTUAL-01,Virtual Product 1,2025-07-01 12:00:00
#4,unfulfilled,5,SKU-E,Product E,2025-07-16 13:00:00
#5,fulfilled,3,SKU-F,Product F,2025-06-30 14:00:00
#6,fulfilled,1,SKU-G,Product G,2025-07-31 23:59:59
#6,fulfilled,1,SKU-H,Product H,2025-08-01 00:00:01
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
    # Orders #1, #3, and #6 (one line item) should be included
    assert results['totals']['processed_orders_count'] == 3
    assert results['totals']['total_units'] == 8 # 2(#1) + 5(#3) + 1(#6)
    assert results['totals']['total_cost_bgn'] == 51.00 # 14(#1) + 25(#3) + 12(#6)
    assert len(results['line_item_df']) == 4 # 1(#1) + 2(#3) + 1(#6)

# Test case 2: SKU exclusion
def test_sku_exclusion(create_test_csv):
    results = calculate_costs(
        filepath=create_test_csv,
        first_sku_cost=10, next_sku_cost=5, unit_cost=2,
        start_date_str="2025-07-01", end_date_str="2025-07-31",
        excluded_skus=["VIRTUAL-01"]
    )
    assert results['error'] is None
    # Orders #1, #3 (minus VIRTUAL-01), and #6 should be included
    assert results['totals']['processed_orders_count'] == 3
    assert results['totals']['total_units'] == 4 # 2(#1) + 1(#3) + 1(#6)
    assert results['totals']['total_cost_bgn'] == 38.00 # 14(#1) + 12(#3) + 12(#6)
    assert len(results['line_item_df']) == 3 # 1(#1) + 1(#3) + 1(#6)

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

# Test case 6: Order with items split across date boundaries
def test_split_date_order(create_test_csv):
    """Ensures only line items within the date range are processed."""
    results = calculate_costs(
        filepath=create_test_csv,
        first_sku_cost=10, next_sku_cost=5, unit_cost=2,
        start_date_str="2025-07-01", end_date_str="2025-07-31"
    )
    # Expected: Order #6 should be processed, but only with SKU-G, not SKU-H.
    # The line_item_df should contain SKU-G but not SKU-H.
    line_items = results['line_item_df']
    assert 'SKU-G' in line_items['SKU'].values
    assert 'SKU-H' not in line_items['SKU'].values

    # Check that the cost for order #6 is calculated correctly (1 sku, 1 unit = 12)
    order_summary = results['order_summary_df']
    order_6_summary = order_summary[order_summary['Order #'] == '#6']
    assert not order_6_summary.empty
    assert order_6_summary.iloc[0]['Order Cost (BGN)'] == 12.00

# Test case 7: Boundary date conditions
def test_boundary_dates(create_test_csv):
    """Tests the very start and end of the date range."""
    results = calculate_costs(
        filepath=create_test_csv,
        first_sku_cost=10, next_sku_cost=5, unit_cost=2,
        start_date_str="2025-07-31", end_date_str="2025-07-31"
    )
    # Only SKU-G from order #6 should be included.
    assert results['totals']['processed_orders_count'] == 1
    assert results['totals']['total_units'] == 1
    assert 'SKU-G' in results['line_item_df']['SKU'].values
    assert len(results['line_item_df']) == 1
