import pytest
import pandas as pd
from src.app.calculator_logic import calculate_costs

@pytest.fixture
def create_test_csv(tmp_path):
    """Creates a temporary CSV file for testing with the new required columns."""
    # Note: Fulfillment Status is no longer needed by the core logic
    csv_content = """Name,Lineitem quantity,Lineitem sku,Lineitem name,Fulfilled at
#1,2,SKU-A,Product A,2025-07-15 10:00:00
#2,1,SKU-B,Product B,2025-08-01 11:00:00
#3,1,SKU-D,Product D,2025-07-01 12:00:00
#3,4,SKU-C,Product C,2025-07-01 12:00:00
#4,5,SKU-E,Product E,
#5,3,SKU-F,Product F,2025-06-30 14:00:00
#6,1,SKU-G,Product G,2025-07-31 23:59:59
#7,1,SKU-I,Product I,2025-07-10 10:00:00
#7,2,SKU-J,Product J,2025-07-10 10:00:00
#8,5,SKU-K,Product K,2025-07-12 10:00:00
"""
    csv_path = tmp_path / "test_data.csv"
    csv_path.write_text(csv_content)
    return str(csv_path)

# Tariffs for testing
# T1: 10, T2: 5, T3: 2
FIRST_SKU_COST = 10
NEXT_SKU_COST = 5
UNIT_COST = 2

# --- Test Cases based on the new logic ---

def test_successful_calculation(create_test_csv):
    """Test a standard calculation within a date range."""
    results = calculate_costs(
        filepath=create_test_csv,
        first_sku_cost=FIRST_SKU_COST, next_sku_cost=NEXT_SKU_COST, unit_cost=UNIT_COST,
        start_date_str="2025-07-01", end_date_str="2025-07-31"
    )

    assert results['error'] is None
    summary = results['summary']

    # Expected Orders: #1, #3, #6, #7, #8
    # Order #1: N=1, Q=2. Cost = 10 + 2*2 = 14
    # Order #3: N=2, Q=5. Cost = 10 + (1*5) + 5*2 = 25
    # Order #6: N=1, Q=1. Cost = 10 + 1*2 = 12
    # Order #7: N=2, Q=3. Cost = 10 + (1*5) + 3*2 = 21
    # Order #8: N=1, Q=5. Cost = 10 + 5*2 = 20
    # Total Orders: 5
    # Total Units: 2+5+1+3+5 = 16
    # Total Cost: 14+25+12+21+20 = 92

    assert summary['total_orders'] == 5
    assert summary['total_units'] == 16
    assert summary['total_cost'] == 92.00
    assert len(results['order_details']) == 5

def test_sku_exclusion(create_test_csv):
    """Test calculation with user-excluded SKUs."""
    results = calculate_costs(
        filepath=create_test_csv,
        first_sku_cost=FIRST_SKU_COST, next_sku_cost=NEXT_SKU_COST, unit_cost=UNIT_COST,
        start_date_str="2025-07-01", end_date_str="2025-07-31",
        excluded_skus=["SKU-C", "SKU-I"]
    )
    assert results['error'] is None
    summary = results['summary']

    # Expected Orders: #1, #3, #6, #7, #8
    # Order #1: N=1, Q=2. Cost = 14
    # Order #3: N=1 (SKU-C excluded), Q=1. Cost = 10 + 1*2 = 12
    # Order #6: N=1, Q=1. Cost = 12
    # Order #7: N=1 (SKU-I excluded), Q=2. Cost = 10 + 2*2 = 14
    # Order #8: N=1, Q=5. Cost = 20
    # Total Orders: 5
    # Total Units: 2+1+1+2+5 = 11
    # Total Cost: 14+12+12+14+20 = 72

    assert summary['total_orders'] == 5
    assert summary['total_units'] == 11
    assert summary['total_cost'] == 72.00

def test_order_ignored_if_all_skus_excluded(create_test_csv):
    """Test that an order is completely ignored if all its SKUs are excluded."""
    results = calculate_costs(
        filepath=create_test_csv,
        first_sku_cost=FIRST_SKU_COST, next_sku_cost=NEXT_SKU_COST, unit_cost=UNIT_COST,
        start_date_str="2025-07-01", end_date_str="2025-07-31",
        excluded_skus=["SKU-A"]
    )
    assert results['error'] is None
    # Order #1 should be missing from the results
    assert results['summary']['total_orders'] == 4
    order_numbers = [d['Номер замовлення'] for d in results['order_details']]
    assert '#1' not in order_numbers

def test_missing_column(tmp_path):
    """Test error handling for a missing required column."""
    csv_content = "Name,Lineitem quantity\n#1,2" # Missing 'Lineitem sku' and 'Fulfilled at'
    csv_path = tmp_path / "bad_data.csv"
    csv_path.write_text(csv_content)
    results = calculate_costs(str(csv_path), FIRST_SKU_COST, NEXT_SKU_COST, UNIT_COST)
    assert 'відсутній обов\'язковий стовпець' in results['error']

def test_no_orders_in_date_range(create_test_csv):
    """Test a date range that yields no results."""
    results = calculate_costs(
        filepath=create_test_csv,
        first_sku_cost=FIRST_SKU_COST, next_sku_cost=NEXT_SKU_COST, unit_cost=UNIT_COST,
        start_date_str="2024-01-01", end_date_str="2024-01-31"
    )
    assert results['error'] is None
    assert results['summary']['total_orders'] == 0
    assert results['summary']['total_cost'] == 0.00
    assert len(results['order_details']) == 0

def test_file_not_found():
    """Test error handling for a non-existent file."""
    results = calculate_costs("non_existent_file.csv", FIRST_SKU_COST, NEXT_SKU_COST, UNIT_COST)
    assert 'файл не знайдено' in results['error']

def test_orders_with_no_fulfillment_date_are_ignored(create_test_csv):
    """Test that orders with blank 'Fulfilled at' are ignored."""
    # Calculate for all time to ensure we're not just filtering by date
    results = calculate_costs(
        filepath=create_test_csv,
        first_sku_cost=FIRST_SKU_COST, next_sku_cost=NEXT_SKU_COST, unit_cost=UNIT_COST
    )
    assert results['error'] is None
    order_numbers = [d['Номер замовлення'] for d in results['order_details']]
    # Order #4 has no fulfillment date and should be ignored
    assert '#4' not in order_numbers
