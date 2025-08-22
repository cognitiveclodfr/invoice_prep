import pytest
import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QDate

from src.app.main_app import MainWindow

@pytest.fixture
def app(qtbot):
    """Create a QApplication and the main window for testing."""
    test_app = QApplication.instance()
    if test_app is None:
        test_app = QApplication(sys.argv)

    window = MainWindow()
    qtbot.addWidget(window)
    return window

@pytest.fixture
def create_test_csv_for_ui(tmp_path):
    """Creates a temporary CSV file for UI testing."""
    csv_content = """Name,Fulfillment Status,Lineitem quantity,Lineitem sku,Lineitem name,Fulfilled at
#101,fulfilled,2,SKU-A,Product A,2025-07-15 10:00:00
#102,fulfilled,1,SKU-D,Product D,2025-07-20 12:00:00
#102,fulfilled,4,VIRTUAL-UI,Virtual UI Product,2025-07-20 12:00:00
"""
    csv_path = tmp_path / "ui_test_data.csv"
    csv_path.write_text(csv_content)
    return str(csv_path)

def test_full_ui_flow(qtbot, app, create_test_csv_for_ui):
    """Test the full user flow programmatically."""
    # Expected results
    expected_orders = "2"
    expected_units = "3" # 2 from #101, 1 from #102 (VIRTUAL-UI excluded)
    expected_bgn = "26.00" # #101 (1 sku, 2 units)=14. #102 (1 sku, 1 unit)=12. Total=26.
    expected_eur = "13.29"
    expected_table_rows = 2

    # 1. Simulate setting the file path
    app.filepath_edit.setText(create_test_csv_for_ui)

    # 2. Simulate setting dates and excluded SKU
    app.start_date_edit.setDate(QDate(2025, 7, 1))
    app.end_date_edit.setDate(QDate(2025, 7, 31))
    app.exclude_skus_edit.setText("VIRTUAL-UI")

    # 3. Simulate clicking the calculate button
    app.calculate_button.click()

    # 4. Wait for the worker's finished signal before asserting
    qtbot.waitSignal(app.worker.finished, timeout=5000)

    # 5. Wait for the UI to update by checking one of the result labels
    qtbot.waitUntil(lambda: app.processed_orders_value.text() == expected_orders, timeout=1000)

    # 6. Assert that the UI updated correctly
    assert app.processed_orders_value.text() == expected_orders
    assert app.total_units_value.text() == expected_units
    assert app.total_cost_bgn_value.text() == expected_bgn
    assert app.total_cost_eur_value.text() == expected_eur

    # Assert table has the correct number of rows
    model = app.orders_table.model()
    assert model.rowCount() == expected_table_rows

    # 5. Test the table filter
    app.filter_edit.setText("#101")
    assert model.rowCount() == 1

    app.filter_edit.setText("") # Clear filter
    assert model.rowCount() == 2
