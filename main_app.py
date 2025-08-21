import sys
import pandas as pd
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QGridLayout, QHBoxLayout,
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
            # Format floating point numbers to 2 decimal places
            value = self._dataframe.iloc[index.row(), index.column()]
            if isinstance(value, float):
                return f"{value:.2f}"
            return str(value)
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

        # To store results for export
        self.results_data = {}

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

        # --- SKU Filter ---
        sku_filter_group = QGroupBox("SKU Filtering")
        sku_filter_layout = QGridLayout()
        self.exclude_skus_edit = QLineEdit()
        self.exclude_skus_edit.setPlaceholderText("e.g., VIRTUAL-01, VIRTUAL-02")
        sku_filter_layout.addWidget(QLabel("Exclude SKUs (comma-separated):"), 0, 0)
        sku_filter_layout.addWidget(self.exclude_skus_edit, 0, 1)
        sku_filter_group.setLayout(sku_filter_layout)
        main_layout.addWidget(sku_filter_group)

        # --- Action Buttons ---
        action_layout = QHBoxLayout()
        self.calculate_button = QPushButton("Calculate Costs")
        self.export_button = QPushButton("Export to XLSX")
        self.export_button.setEnabled(False)
        action_layout.addWidget(self.calculate_button)
        action_layout.addWidget(self.export_button)
        main_layout.addLayout(action_layout)

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
        self.filter_edit.setPlaceholderText("Filter by Order #, SKU, or Product Name...")
        self.orders_table = QTableView()
        self.orders_table.setSortingEnabled(True)
        results_layout.addWidget(self.filter_edit)
        results_layout.addWidget(self.orders_table)
        results_group.setLayout(results_layout)
        main_layout.addWidget(results_group)

        # Connections
        self.browse_button.clicked.connect(self.open_file_dialog)
        self.calculate_button.clicked.connect(self.run_calculation)
        self.export_button.clicked.connect(self.export_to_xlsx)
        self.filter_edit.textChanged.connect(self.filter_table)

    def open_file_dialog(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "Open CSV", "", "CSV Files (*.csv);;All Files (*)")
        if filepath:
            self.filepath_edit.setText(filepath)

    def run_calculation(self):
        filepath = self.filepath_edit.text()
        if not filepath:
            QMessageBox.warning(self, "Warning", "Please select a CSV file.")
            return

        start_date = self.start_date_edit.date().toString("yyyy-MM-dd")
        end_date = self.end_date_edit.date().toString("yyyy-MM-dd")

        excluded_skus_str = self.exclude_skus_edit.text()
        excluded_skus = [sku.strip() for sku in excluded_skus_str.split(',') if sku.strip()]

        self.results_data = calculate_costs(
            filepath=filepath,
            first_sku_cost=self.first_sku_spinbox.value(),
            next_sku_cost=self.next_sku_spinbox.value(),
            unit_cost=self.unit_cost_spinbox.value(),
            start_date_str=start_date,
            end_date_str=end_date,
            excluded_skus=excluded_skus
        )

        if self.results_data.get('error'):
            QMessageBox.critical(self, "Error", self.results_data['error'])
            self.export_button.setEnabled(False)
        else:
            totals = self.results_data['totals']
            self.processed_orders_value.setText(str(totals['processed_orders_count']))
            self.total_units_value.setText(str(totals['total_units']))
            self.total_cost_bgn_value.setText(f"{totals['total_cost_bgn']:.2f}")
            self.total_cost_eur_value.setText(f"{totals['total_cost_eur']:.2f}")

            line_item_df = self.results_data['line_item_df']
            self.model = PandasModel(line_item_df)

            self.proxy_model = QSortFilterProxyModel()
            self.proxy_model.setSourceModel(self.model)
            self.proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)
            self.proxy_model.setFilterKeyColumn(-1) # Search all columns

            self.orders_table.setModel(self.proxy_model)
            self.orders_table.resizeColumnsToContents()

            self.export_button.setEnabled(True)

    def filter_table(self, text):
        if hasattr(self, 'proxy_model'):
            self.proxy_model.setFilterRegularExpression(text)

    def export_to_xlsx(self):
        if not self.results_data or self.results_data.get('error'):
            QMessageBox.warning(self, "Warning", "No valid data available to export.")
            return

        save_path, _ = QFileDialog.getSaveFileName(self, "Save Excel File", "", "Excel Files (*.xlsx)")
        if not save_path:
            return

        try:
            with pd.ExcelWriter(save_path, engine='openpyxl') as writer:
                # Sheet 1: Detailed Line Items
                self.results_data['line_item_df'].to_excel(writer, sheet_name='Filtered Line Items', index=False)

                # Sheet 2: Per-Order Summary
                self.results_data['order_summary_df'].to_excel(writer, sheet_name='Order Summaries', index=False)

                # Sheet 3: Grand Totals
                totals_df = pd.DataFrame([self.results_data['totals']])
                totals_df.to_excel(writer, sheet_name='Grand Totals', index=False)

                # Auto-adjust column widths for readability
                for sheet_name in writer.sheets:
                    worksheet = writer.sheets[sheet_name]
                    for column in worksheet.columns:
                        max_length = 0
                        column_letter = column[0].column_letter
                        for cell in column:
                            try:
                                if len(str(cell.value)) > max_length:
                                    max_length = len(str(cell.value))
                            except:
                                pass
                        adjusted_width = (max_length + 2)
                        worksheet.column_dimensions[column_letter].width = adjusted_width

            QMessageBox.information(self, "Success", f"Data successfully exported to {save_path}")

        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"An error occurred during export: {e}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
