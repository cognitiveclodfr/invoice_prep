# Fulfillment Cost Calculator Desktop Application

This project is a local desktop application for automatically calculating the cost of fulfillment services based on exported data from Shopify.

## Description

The application allows users to upload a standard CSV order export file from Shopify, filter orders by a fulfillment date range, configure tariffs, and receive a calculation of the total cost for processing the orders. The results are displayed in a filterable table.

## Technologies

- **Core Logic**: Python, Pandas
- **GUI**: PySide6

## CSV File Requirements

For the application to work correctly, the uploaded CSV file must contain the following columns:

- `Fulfillment Status` - The fulfillment status of the order.
- `Name` - The unique order number.
- `Lineitem quantity` - The quantity of a product in a line item.
- `Lineitem sku` - The SKU of the product.
- `Lineitem name` - The name of the product.
- `Fulfilled at` - The date the order was fulfilled. The date format should be understandable by pandas (e.g., `YYYY-MM-DD HH:MM:SS`).

## Installation and Launch

1.  **Clone the repository or download the code archive.**

2.  **Create and activate a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # For Windows: venv\Scripts\activate
    ```

3.  **Install the necessary dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Launch the application:**
    ```bash
    python main_app.py
    ```

## How to Use

1.  Launch the application by running the `main_app.py` script.
2.  Click the "Browse..." button to select your `.csv` export file from Shopify.
3.  Select a "Start Date" and "End Date" to filter orders by their fulfillment date.
4.  Check or change the tariff values (in BGN).
5.  Optionally, enter any SKUs you wish to exclude from the calculation in the "Exclude SKUs" field, separated by commas.
6.  Click the "Calculate Costs" button.
7.  The results will appear, showing summary totals and a detailed table of all processed line items.
8.  You can type in the filter box above the table to search across all columns.
9.  Click the "Export to XLSX" button to save the results. This will create an Excel file with three sheets: detailed line items, a summary for each order, and the grand totals.
