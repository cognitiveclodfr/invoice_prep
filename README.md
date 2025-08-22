# Fulfillment Cost Calculator Desktop Application

This project is a local desktop application for automatically calculating the cost of fulfillment services based on exported data from Shopify.

## Project Structure

The project is organized as follows:
- `main.py`: The entry point to launch the application.
- `src/app/`: Contains the main application source code.
  - `main_app.py`: The GUI and main application window logic.
  - `calculator_logic.py`: The core business logic for data processing and calculation.
- `tests/`: Contains the test suite.
- `requirements.txt`: Project dependencies.
- `.gitignore`: Specifies files to be ignored by Git.
- `pytest.ini`: Configuration file for pytest.
- `.github/workflows/`: Contains the GitHub Actions workflow for building releases.

## Features
- Load and parse Shopify order data from a CSV file.
- Filter orders by a specific date range.
- Exclude specific SKUs from the calculation.
- Calculate fulfillment costs based on a multi-component tariff.
- Display detailed results in a filterable, sortable table.
- Export results to a multi-sheet XLSX file for analysis.

## CSV File Requirements
For the application to work correctly, the uploaded CSV file must contain the following columns:
- `Fulfillment Status`
- `Name` (Order Number)
- `Lineitem quantity`
- `Lineitem sku`
- `Lineitem name`
- `Fulfilled at`

## Installation and Launch

1.  **Clone the repository.**
2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # For Windows: venv\Scripts\activate
    ```
3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Launch the application:**
    ```bash
    python main.py
    ```

## How to Use

1.  Launch the application by running the `main.py` script.
2.  Click the "Browse..." button to select your `.csv` export file.
3.  Select a "Start Date" and "End Date" to filter orders.
4.  Adjust the tariffs and the EUR to BGN exchange rate in the settings area if needed.
5.  Optionally, enter SKUs to exclude from the calculation (comma-separated).
6.  Click "Calculate Costs" to process the data. The UI will remain responsive while calculating.
7.  View the results in the summary panel and the detailed table.
8.  Click "Export to XLSX" to save a multi-sheet Excel report.

## Running Tests

This project uses `pytest` for testing. To run the test suite:

1.  Make sure you have installed the development dependencies from `requirements.txt`.
2.  From the root directory of the project, run:
    ```bash
    pytest
    ```
This will discover and run all tests in the `tests/` directory.
