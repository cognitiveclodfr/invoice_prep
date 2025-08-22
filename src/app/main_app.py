import sys
import pandas as pd
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QGridLayout, QHBoxLayout,
    QPushButton, QLineEdit, QLabel, QDateEdit, QDoubleSpinBox,
    QTableView, QGroupBox, QFileDialog, QMessageBox
)
from PySide6.QtCore import QDate, Qt, QAbstractTableModel, QSortFilterProxyModel, QObject, Signal, QThread, QTimer
from .calculator_logic import calculate_costs

# --- Worker for background processing ---
class Worker(QObject):
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, filepath, first_sku_cost, next_sku_cost, unit_cost,
                 eur_to_bgn_rate, start_date_str, end_date_str, excluded_skus):
        super().__init__()
        self.filepath = filepath
        self.first_sku_cost = first_sku_cost
        self.next_sku_cost = next_sku_cost
        self.unit_cost = unit_cost
        self.eur_to_bgn_rate = eur_to_bgn_rate
        self.start_date_str = start_date_str
        self.end_date_str = end_date_str
        self.excluded_skus = excluded_skus

    def run(self):
        """Long-running task."""
        try:
            results = calculate_costs(
                self.filepath, self.first_sku_cost, self.next_sku_cost, self.unit_cost,
                self.eur_to_bgn_rate, self.start_date_str, self.end_date_str, self.excluded_skus
            )
            if results.get('error'):
                self.error.emit(results['error'])
            else:
                self.finished.emit(results)
        except Exception as e:
            self.error.emit(f"An unexpected critical error occurred: {e}")

# --- Pandas Model for TableView ---
class PandasModel(QAbstractTableModel):
    def __init__(self, dataframe: pd.DataFrame, parent=None):
        QAbstractTableModel.__init__(self, parent)
        self._dataframe = dataframe

    def rowCount(self, parent=None):
        return self._dataframe.shape[0]

    def columnCount(self, parent=None):
        return self._dataframe.shape[1]

    def data(self, index, role=Qt.DisplayRole):
        if index.isValid() and role == Qt.DisplayRole:
            value = self._dataframe.iloc[index.row(), index.column()]
            if isinstance(value, float):
                return f"{value:.2f}"
            return str(value)
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self._dataframe.columns[section]
        return None

# --- Main Application Window ---
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Fulfillment Cost Calculator")
        self.setGeometry(100, 100, 800, 700)

        self.results_data = {}
        self.thread = None
        self.worker = None

        # Debounce timer for the filter
        self.filter_timer = QTimer(self)
        self.filter_timer.setSingleShot(True)
        self.filter_timer.setInterval(300) # 300ms delay

        self.setup_ui()
        self.connect_signals()

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        self.create_inputs_group(main_layout)
        self.create_tariffs_group(main_layout)
        self.create_sku_filter_group(main_layout)
        self.create_action_buttons(main_layout)
        self.create_results_group(main_layout)

    def create_inputs_group(self, layout):
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
        layout.addWidget(inputs_group)

    def create_tariffs_group(self, layout):
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
        self.exchange_rate_spinbox = QDoubleSpinBox()
        self.exchange_rate_spinbox.setDecimals(5)
        self.exchange_rate_spinbox.setRange(0.1, 10.0)
        self.exchange_rate_spinbox.setValue(1.95583)
        tariffs_layout.addWidget(QLabel("EUR to BGN Rate:"), 3, 0)
        tariffs_layout.addWidget(self.exchange_rate_spinbox, 3, 1)
        tariffs_group.setLayout(tariffs_layout)
        layout.addWidget(tariffs_group)

    def create_sku_filter_group(self, layout):
        sku_filter_group = QGroupBox("SKU Filtering")
        sku_filter_layout = QGridLayout()
        self.exclude_skus_edit = QLineEdit()
        self.exclude_skus_edit.setPlaceholderText("e.g., VIRTUAL-01, parcel-protection")
        sku_filter_layout.addWidget(QLabel("Exclude SKUs (comma-separated):"), 0, 0)
        sku_filter_layout.addWidget(self.exclude_skus_edit, 0, 1)
        sku_filter_group.setLayout(sku_filter_layout)
        layout.addWidget(sku_filter_group)

    def create_action_buttons(self, layout):
        action_layout = QHBoxLayout()
        self.calculate_button = QPushButton("Calculate Costs")
        self.export_button = QPushButton("Export to XLSX")
        self.export_button.setEnabled(False)
        action_layout.addWidget(self.calculate_button)
        action_layout.addWidget(self.export_button)
        layout.addLayout(action_layout)

    def create_results_group(self, layout):
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
        layout.addWidget(results_group)

    def connect_signals(self):
        self.browse_button.clicked.connect(self.open_file_dialog)
        self.calculate_button.clicked.connect(self.run_calculation)
        self.export_button.clicked.connect(self.export_to_xlsx)
        # Debounced filter
        self.filter_edit.textChanged.connect(self.filter_timer.start)
        self.filter_timer.timeout.connect(self.apply_filter)

    def open_file_dialog(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "Open CSV", "", "CSV Files (*.csv);;All Files (*)")
        if filepath:
            self.filepath_edit.setText(filepath)

    def run_calculation(self):
        if not self.filepath_edit.text():
            QMessageBox.warning(self, "Warning", "Please select a CSV file.")
            return

        self.calculate_button.setEnabled(False)
        self.calculate_button.setText("Calculating...")
        self.export_button.setEnabled(False)

        self.thread = QThread()
        self.worker = Worker(
            filepath=self.filepath_edit.text(),
            first_sku_cost=self.first_sku_spinbox.value(),
            next_sku_cost=self.next_sku_spinbox.value(),
            unit_cost=self.unit_cost_spinbox.value(),
            eur_to_bgn_rate=self.exchange_rate_spinbox.value(),
            start_date_str=self.start_date_edit.date().toString("yyyy-MM-dd"),
            end_date_str=self.end_date_edit.date().toString("yyyy-MM-dd"),
            excluded_skus=[sku.strip() for sku in self.exclude_skus_edit.text().split(',') if sku.strip()]
        )
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.on_calculation_finished)
        self.worker.error.connect(self.on_calculation_error)
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.finished.connect(self.thread.quit)
        self.worker.error.connect(self.thread.quit)
        self.thread.start()

    def on_calculation_finished(self, results):
        self.results_data = results
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
        self.proxy_model.setFilterKeyColumn(-1)
        self.orders_table.setModel(self.proxy_model)
        self.orders_table.resizeColumnsToContents()

        self.calculate_button.setEnabled(True)
        self.calculate_button.setText("Calculate Costs")
        self.export_button.setEnabled(True)

    def on_calculation_error(self, error_message):
        QMessageBox.critical(self, "Error", error_message)
        self.calculate_button.setEnabled(True)
        self.calculate_button.setText("Calculate Costs")
        self.export_button.setEnabled(False)

    def apply_filter(self):
        """Applies the filter to the table view."""
        if hasattr(self, 'proxy_model'):
            text = self.filter_edit.text()
            self.proxy_model.setFilterRegularExpression(text)

    def export_to_xlsx(self):
        if not self.results_data or self.results_data.get('error'):
            QMessageBox.warning(self, "Warning", "No valid data to export.")
            return

        save_path, _ = QFileDialog.getSaveFileName(self, "Save Excel File", "", "Excel Files (*.xlsx)")
        if not save_path:
            return

        try:
            with pd.ExcelWriter(save_path, engine='openpyxl') as writer:
                # Sheet 1: Get visible data from proxy model
                if hasattr(self, 'proxy_model'):
                    rows = self.proxy_model.rowCount()
                    cols = self.proxy_model.columnCount()
                    visible_data = []
                    for row in range(rows):
                        row_data = [self.proxy_model.index(row, col).data() for col in range(cols)]
                        visible_data.append(row_data)

                    header_labels = [self.proxy_model.headerData(i, Qt.Horizontal) for i in range(cols)]
                    export_df = pd.DataFrame(visible_data, columns=header_labels)
                    export_df.to_excel(writer, sheet_name='Filtered Line Items', index=False)

                # Sheet 2: Per-Order Summary
                self.results_data['order_summary_df'].to_excel(writer, sheet_name='Order Summaries', index=False)

                # Sheet 3: Grand Totals
                totals_df = pd.DataFrame([self.results_data['totals']])
                totals_df.to_excel(writer, sheet_name='Grand Totals', index=False)

            QMessageBox.information(self, "Success", f"Data successfully exported to {save_path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"An error occurred during export: {e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
