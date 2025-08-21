import sys
import pandas as pd
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QGridLayout,
    QPushButton, QLineEdit, QLabel, QDateEdit, QDoubleSpinBox,
    QTableView, QGroupBox, QFileDialog, QMessageBox
)
from PySide6.QtCore import QDate, Qt, QAbstractTableModel, QSortFilterProxyModel
from calculator_logic import calculate_costs

class PandasModel(QAbstractTableModel):
    """A model to interface a pandas DataFrame with QTableView."""
    def __init__(self, dataframe: pd.DataFrame, parent=None):
        QAbstractTableModel.__init__(self, parent)
        self._dataframe = dataframe

    def rowCount(self, parent=None):
        return self._dataframe.shape[0]

    def columnCount(self, parent=None):
        return self._dataframe.shape[1]

    def data(self, index, role=Qt.DisplayRole):
        if index.isValid() and role == Qt.DisplayRole:
            return str(self._dataframe.iloc[index.row(), index.column()])
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self._dataframe.columns[section]
        return None

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Fulfillment Cost Calculator")
        self.setGeometry(100, 100, 800, 700)

        # Main widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # --- Inputs Group ---
        inputs_group = QGroupBox("Inputs")
        inputs_layout = QGridLayout()

        self.filepath_edit = QLineEdit()
        self.filepath_edit.setReadOnly(True)
        self.browse_button = QPushButton("Browse...")
        inputs_layout.addWidget(QLabel("CSV File:"), 0, 0)
        inputs_layout.addWidget(self.filepath_edit, 0, 1, 1, 2)
        inputs_layout.addWidget(self.browse_button, 0, 3)

        self.start_date_edit = QDateEdit(calendarPopup=True)
        self.start_date_edit.setDate(QDate.currentDate().addMonths(-1))
        self.end_date_edit = QDateEdit(calendarPopup=True)
        self.end_date_edit.setDate(QDate.currentDate())
        inputs_layout.addWidget(QLabel("Start Date:"), 1, 0)
        inputs_layout.addWidget(self.start_date_edit, 1, 1)
        inputs_layout.addWidget(QLabel("End Date:"), 1, 2)
        inputs_layout.addWidget(self.end_date_edit, 1, 3)

        inputs_group.setLayout(inputs_layout)
        main_layout.addWidget(inputs_group)

        # --- Tariffs Group ---
        tariffs_group = QGroupBox("Tariff Settings (in BGN)")
        tariffs_layout = QGridLayout()
        self.first_sku_spinbox = QDoubleSpinBox()
        self.first_sku_spinbox.setRange(0, 10000)
        self.first_sku_spinbox.setValue(10.00)
        self.next_sku_spinbox = QDoubleSpinBox()
        self.next_sku_spinbox.setRange(0, 10000)
        self.next_sku_spinbox.setValue(5.00)
        self.unit_cost_spinbox = QDoubleSpinBox()
        self.unit_cost_spinbox.setRange(0, 10000)
        self.unit_cost_spinbox.setValue(2.00)
        tariffs_layout.addWidget(QLabel("Cost for first unique SKU:"), 0, 0)
        tariffs_layout.addWidget(self.first_sku_spinbox, 0, 1)
        tariffs_layout.addWidget(QLabel("Cost for subsequent unique SKU:"), 1, 0)
        tariffs_layout.addWidget(self.next_sku_spinbox, 1, 1)
        tariffs_layout.addWidget(QLabel("Cost per unit:"), 2, 0)
        tariffs_layout.addWidget(self.unit_cost_spinbox, 2, 1)
        tariffs_group.setLayout(tariffs_layout)
        main_layout.addWidget(tariffs_group)

        # --- Calculate Button ---
        self.calculate_button = QPushButton("Calculate Costs")
        main_layout.addWidget(self.calculate_button)

        # --- Results Group ---
        results_group = QGroupBox("Results")
        results_layout = QVBoxLayout()
        summary_layout = QGridLayout()
        self.processed_orders_value = QLabel("0")
        self.total_units_value = QLabel("0")
        self.total_cost_bgn_value = QLabel("0.00")
        self.total_cost_eur_value = QLabel("0.00")
        summary_layout.addWidget(QLabel("Processed Orders:"), 0, 0)
        summary_layout.addWidget(self.processed_orders_value, 0, 1)
        summary_layout.addWidget(QLabel("Total Units:"), 1, 0)
        summary_layout.addWidget(self.total_units_value, 1, 1)
        summary_layout.addWidget(QLabel("Total Cost (BGN):"), 2, 0)
        summary_layout.addWidget(self.total_cost_bgn_value, 2, 1)
        summary_layout.addWidget(QLabel("Total Cost (EUR):"), 3, 0)
        summary_layout.addWidget(self.total_cost_eur_value, 3, 1)
        results_layout.addLayout(summary_layout)

        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("Filter by Order #...")
        self.orders_table = QTableView()
        self.orders_table.setSortingEnabled(True)
        results_layout.addWidget(self.filter_edit)
        results_layout.addWidget(self.orders_table)
        results_group.setLayout(results_layout)
        main_layout.addWidget(results_group)

        # Connections
        self.browse_button.clicked.connect(self.open_file_dialog)
        self.calculate_button.clicked.connect(self.run_calculation)
        self.filter_edit.textChanged.connect(self.filter_table)

    def open_file_dialog(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "Open CSV", "", "CSV Files (*.csv)")
        if filepath:
            self.filepath_edit.setText(filepath)

    def run_calculation(self):
        filepath = self.filepath_edit.text()
        if not filepath:
            QMessageBox.warning(self, "Warning", "Please select a CSV file.")
            return

        start_date = self.start_date_edit.date().toString("yyyy-MM-dd")
        end_date = self.end_date_edit.date().toString("yyyy-MM-dd")

        results = calculate_costs(
            filepath=filepath,
            first_sku_cost=self.first_sku_spinbox.value(),
            next_sku_cost=self.next_sku_spinbox.value(),
            unit_cost=self.unit_cost_spinbox.value(),
            start_date_str=start_date,
            end_date_str=end_date
        )

        if results.get('error'):
            QMessageBox.critical(self, "Error", results['error'])
        else:
            self.processed_orders_value.setText(str(results['processed_orders_count']))
            self.total_units_value.setText(str(results['total_units']))
            self.total_cost_bgn_value.setText(f"{results['total_cost_bgn']:.2f}")
            self.total_cost_eur_value.setText(f"{results['total_cost_eur']:.2f}")

            df = pd.DataFrame(results['orders'])
            if not df.empty:
                # Rename columns for display
                df.rename(columns={
                    'name': 'Order #',
                    'unique_skus': 'Unique SKUs',
                    'units': 'Total Units',
                    'cost_bgn': 'Cost (BGN)'
                }, inplace=True)

            self.model = PandasModel(df)

            self.proxy_model = QSortFilterProxyModel()
            self.proxy_model.setSourceModel(self.model)
            self.proxy_model.setFilterKeyColumn(0) # Filter on the first column 'Order #'
            self.proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)

            self.orders_table.setModel(self.proxy_model)
            self.orders_table.resizeColumnsToContents()

    def filter_table(self, text):
        if hasattr(self, 'proxy_model'):
            self.proxy_model.setFilterRegularExpression(text)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
