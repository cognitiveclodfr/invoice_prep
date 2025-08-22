import pytest
import pandas as pd
import time
import random
from src.app.calculator_logic import calculate_costs

def generate_large_csv(filepath, num_rows):
    """Generates a large CSV file for performance testing."""
    data = {
        'Name': [f"#{i//2 + 1}" for i in range(num_rows)],
        'Lineitem quantity': [random.randint(1, 5) for _ in range(num_rows)],
        'Lineitem sku': [f"SKU-{random.randint(1, 100)}" for _ in range(num_rows)],
        'Lineitem name': [f"Product-{random.randint(1, 100)}" for _ in range(num_rows)],
        'Fulfilled at': [pd.Timestamp('2025-07-15 12:00:00') for _ in range(num_rows)]
    }
    df = pd.DataFrame(data)
    df.to_csv(filepath, index=False)

@pytest.mark.performance
def test_performance_with_large_file(tmp_path):
    """Tests the calculation performance on a large file."""
    num_rows = 10000
    large_csv_path = tmp_path / "large_data.csv"
    generate_large_csv(large_csv_path, num_rows)

    start_time = time.time()

    results = calculate_costs(
        filepath=str(large_csv_path),
        first_sku_cost=10, next_sku_cost=5, unit_cost=2,
        start_date_str="2025-07-01", end_date_str="2025-07-31"
    )

    end_time = time.time()
    duration = end_time - start_time

    print(f"Performance test with {num_rows} rows took {duration:.2f} seconds.")

    assert results['error'] is None
    assert results['summary']['total_orders'] > 0
    # Set a reasonable time limit, e.g., 10 seconds.
    # This might need adjustment based on the runner's performance.
    assert duration < 10
