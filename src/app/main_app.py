import sys
import pandas as pd
import json
import os
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QGridLayout, QHBoxLayout,
    QPushButton, QLineEdit, QLabel, QDateEdit, QDoubleSpinBox,
    QTableView, QGroupBox, QFileDialog, QMessageBox
)
from PySide6.QtCore import QDate, Qt, QAbstractTableModel, QSortFilterProxyModel, QObject, Signal, QThread
from .calculator_logic import calculate_costs

# --- Worker for background processing ---
class Worker(QObject):
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, filepath, first_sku_cost, next_sku_cost, unit_cost,
                 start_date_str, end_date_str, excluded_skus):
        super().__init__()
        self.filepath = filepath
        self.first_sku_cost = first_sku_cost
        self.next_sku_cost = next_sku_cost
        self.unit_cost = unit_cost
        self.start_date_str = start_date_str
        self.end_date_str = end_date_str
        self.excluded_skus = excluded_skus

    def run(self):
        """Long-running task."""
        try:
            results = calculate_costs(
                self.filepath, self.first_sku_cost, self.next_sku_cost, self.unit_cost,
                self.start_date_str, self.end_date_str, self.excluded_skus
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
        self.setWindowTitle("Shopify Fulfillment Calculator")
        self.setGeometry(100, 100, 800, 700)

        self.results_data = {}
        self.thread = None
        self.worker = None
        self.settings_file = "settings.json"

        self.setup_ui()
        self.connect_signals()
        self.load_settings()

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
        inputs_group = QGroupBox("1. Вхідні дані та період")
        inputs_layout = QGridLayout()
        self.filepath_edit = QLineEdit()
        self.filepath_edit.setReadOnly(True)
        self.browse_button = QPushButton("Вибрати файл...")
        inputs_layout.addWidget(QLabel("CSV Файл:"), 0, 0)
        inputs_layout.addWidget(self.filepath_edit, 0, 1, 1, 2)
        inputs_layout.addWidget(self.browse_button, 0, 3)
        self.start_date_edit = QDateEdit(calendarPopup=True)
        self.start_date_edit.setDate(QDate.currentDate().addMonths(-1))
        self.end_date_edit = QDateEdit(calendarPopup=True)
        self.end_date_edit.setDate(QDate.currentDate())
        inputs_layout.addWidget(QLabel("З дати:"), 1, 0)
        inputs_layout.addWidget(self.start_date_edit, 1, 1)
        inputs_layout.addWidget(QLabel("По дату:"), 1, 2)
        inputs_layout.addWidget(self.end_date_edit, 1, 3)
        inputs_group.setLayout(inputs_layout)
        layout.addWidget(inputs_group)

    def create_tariffs_group(self, layout):
        tariffs_group = QGroupBox("2. Тарифи (в BGN)")
        tariffs_layout = QGridLayout()
        self.first_sku_spinbox = QDoubleSpinBox()
        self.first_sku_spinbox.setRange(0, 10000)
        self.first_sku_spinbox.setValue(2.30) # Default value
        self.next_sku_spinbox = QDoubleSpinBox()
        self.next_sku_spinbox.setRange(0, 10000)
        self.next_sku_spinbox.setValue(1.10) # Default value
        self.unit_cost_spinbox = QDoubleSpinBox()
        self.unit_cost_spinbox.setRange(0, 10000)
        self.unit_cost_spinbox.setValue(0.40) # Default value
        tariffs_layout.addWidget(QLabel("Вартість за першу товарну позицію (SKU):"), 0, 0)
        tariffs_layout.addWidget(self.first_sku_spinbox, 0, 1)
        tariffs_layout.addWidget(QLabel("Вартість за кожну наступну позицію (SKU):"), 1, 0)
        tariffs_layout.addWidget(self.next_sku_spinbox, 1, 1)
        tariffs_layout.addWidget(QLabel("Вартість за кожну одиницю товару:"), 2, 0)
        tariffs_layout.addWidget(self.unit_cost_spinbox, 2, 1)
        tariffs_group.setLayout(tariffs_layout)
        layout.addWidget(tariffs_group)

    def create_sku_filter_group(self, layout):
        sku_filter_group = QGroupBox("3. Фільтр по SKU")
        sku_filter_layout = QGridLayout()
        self.exclude_skus_edit = QLineEdit()
        self.exclude_skus_edit.setPlaceholderText("напр. VIRTUAL-01, артикул-02, артикул-03")
        sku_filter_layout.addWidget(QLabel("Виключити SKU (через кому):"), 0, 0)
        sku_filter_layout.addWidget(self.exclude_skus_edit, 0, 1)
        sku_filter_group.setLayout(sku_filter_layout)
        layout.addWidget(sku_filter_group)

    def create_action_buttons(self, layout):
        action_layout = QHBoxLayout()
        self.calculate_button = QPushButton("Розрахувати")
        self.export_button = QPushButton("Експорт в Excel")
        self.export_button.setEnabled(False)
        action_layout.addWidget(self.calculate_button)
        action_layout.addWidget(self.export_button)
        layout.addLayout(action_layout)

    def create_results_group(self, layout):
        results_group = QGroupBox("Результати")
        results_layout = QVBoxLayout()
        summary_layout = QGridLayout()
        self.processed_orders_value = QLabel("0")
        self.total_units_value = QLabel("0")
        self.total_cost_bgn_value = QLabel("0.00")
        summary_layout.addWidget(QLabel("Оброблено замовлень:"), 0, 0)
        summary_layout.addWidget(self.processed_orders_value, 0, 1)
        summary_layout.addWidget(QLabel("Всього одиниць товару:"), 1, 0)
        summary_layout.addWidget(self.total_units_value, 1, 1)
        summary_layout.addWidget(QLabel("Загальна вартість (BGN):"), 2, 0)
        summary_layout.addWidget(self.total_cost_bgn_value, 2, 1)
        results_layout.addLayout(summary_layout)

        self.orders_table = QTableView()
        self.orders_table.setSortingEnabled(True)
        results_layout.addWidget(self.orders_table)
        results_group.setLayout(results_layout)
        layout.addWidget(results_group)

    def connect_signals(self):
        self.browse_button.clicked.connect(self.open_file_dialog)
        self.calculate_button.clicked.connect(self.run_calculation)
        self.export_button.clicked.connect(self.export_to_xlsx)

    def open_file_dialog(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "Вибрати CSV", "", "CSV Files (*.csv);;All Files (*)")
        if filepath:
            self.filepath_edit.setText(filepath)

    def run_calculation(self):
        if not self.filepath_edit.text():
            QMessageBox.warning(self, "Увага", "Будь ласка, виберіть CSV файл.")
            return

        self.save_settings()

        self.calculate_button.setEnabled(False)
        self.calculate_button.setText("Розрахунок...")
        self.export_button.setEnabled(False)

        self.thread = QThread()
        self.worker = Worker(
            filepath=self.filepath_edit.text(),
            first_sku_cost=self.first_sku_spinbox.value(),
            next_sku_cost=self.next_sku_spinbox.value(),
            unit_cost=self.unit_cost_spinbox.value(),
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
        summary = self.results_data['summary']
        self.processed_orders_value.setText(str(summary['total_orders']))
        self.total_units_value.setText(str(summary['total_units']))
        self.total_cost_bgn_value.setText(f"{summary['total_cost']:.2f}")

        order_details_df = pd.DataFrame(self.results_data.get('order_details', []))
        self.model = PandasModel(order_details_df)

        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.model)
        self.orders_table.setModel(self.proxy_model)
        self.orders_table.resizeColumnsToContents()

        self.calculate_button.setEnabled(True)
        self.calculate_button.setText("Розрахувати")
        self.export_button.setEnabled(True)

    def on_calculation_error(self, error_message):
        QMessageBox.critical(self, "Помилка", error_message)
        self.calculate_button.setEnabled(True)
        self.calculate_button.setText("Розрахувати")
        self.export_button.setEnabled(False)

    def save_settings(self):
        """Saves current UI settings to a JSON file."""
        settings = {
            'first_sku_cost': self.first_sku_spinbox.value(),
            'next_sku_cost': self.next_sku_spinbox.value(),
            'unit_cost': self.unit_cost_spinbox.value(),
            'start_date': self.start_date_edit.date().toString("yyyy-MM-dd"),
            'end_date': self.end_date_edit.date().toString("yyyy-MM-dd"),
            'excluded_skus': self.exclude_skus_edit.text(),
            'last_csv_path': self.filepath_edit.text()
        }
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(settings, f, indent=4)
        except IOError as e:
            print(f"Error saving settings: {e}")

    def load_settings(self):
        """Loads settings from a JSON file and applies them to the UI."""
        if not os.path.exists(self.settings_file):
            return # No settings file yet, use defaults
        try:
            with open(self.settings_file, 'r') as f:
                settings = json.load(f)

            self.first_sku_spinbox.setValue(settings.get('first_sku_cost', 2.30))
            self.next_sku_spinbox.setValue(settings.get('next_sku_cost', 1.10))
            self.unit_cost_spinbox.setValue(settings.get('unit_cost', 0.40))

            if 'start_date' in settings:
                self.start_date_edit.setDate(QDate.fromString(settings['start_date'], "yyyy-MM-dd"))
            if 'end_date' in settings:
                self.end_date_edit.setDate(QDate.fromString(settings['end_date'], "yyyy-MM-dd"))

            self.exclude_skus_edit.setText(settings.get('excluded_skus', ''))
            self.filepath_edit.setText(settings.get('last_csv_path', ''))

        except (IOError, json.JSONDecodeError) as e:
            print(f"Error loading settings: {e}")

    def export_to_xlsx(self):
        if not self.results_data or self.results_data.get('error'):
            QMessageBox.warning(self, "Warning", "Немає даних для експорту.")
            return

        save_path, _ = QFileDialog.getSaveFileName(self, "Зберегти Excel файл", "", "Excel Files (*.xlsx)")
        if not save_path:
            return

        try:
            with pd.ExcelWriter(save_path, engine='openpyxl') as writer:
                # Sheet 1: Detailed report of all processed orders
                details_df = pd.DataFrame(self.results_data['order_details'])
                details_df.to_excel(writer, sheet_name='Детальний звіт по замовленнях', index=False)

                # Sheet 2: Summary report with cost breakdown
                summary_data = self.results_data['summary']
                summary_df = pd.DataFrame({
                    'Параметр': [
                        'Загальна кількість оброблених замовлень',
                        'Загальна кількість одиниць товару',
                        'Загальна вартість від перших позицій (BGN)',
                        'Загальна вартість від наступних позицій (BGN)',
                        'Загальна вартість від одиниць товару (BGN)',
                        'ВСЬОГО (BGN)'
                    ],
                    'Значення': [
                        summary_data['total_orders'],
                        summary_data['total_units'],
                        summary_data['cost_from_first_sku'],
                        summary_data['cost_from_next_sku'],
                        summary_data['cost_from_unit'],
                        summary_data['total_cost']
                    ]
                })
                summary_df.to_excel(writer, sheet_name='Підсумковий звіт', index=False)

            QMessageBox.information(self, "Успіх", f"Дані успішно експортовано до {save_path}")
        except Exception as e:
            QMessageBox.critical(self, "Помилка експорту", f"Під час експорту сталася помилка: {e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
