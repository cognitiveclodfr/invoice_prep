# Fulfillment Cost Calculator Application

This project is a local single-page web application for automatically calculating the cost of fulfillment services based on exported data from Shopify.

## Description

The application allows users to upload a standard CSV order export file from Shopify, configure tariffs, and receive a calculation of the total cost for processing the orders.

## Technologies

- **Backend**: Python, Flask, Pandas
- **Frontend**: HTML, CSS, JavaScript

## CSV File Requirements

For the application to work correctly, the uploaded CSV file must contain the following columns:

- `Fulfillment Status` - The fulfillment status of the order.
- `Name` - The unique order number.
- `Lineitem quantity` - The quantity of a product in a line item.
- `Lineitem sku` - The SKU of the product.
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
    python app.py
    ```

5.  **Open a web browser** and navigate to the address shown in the terminal (usually `http://127.0.0.1:5000`).

## How to Use

1.  Open the application page in your browser.
2.  Click the "Choose File" button (or similar) and select your `.csv` export file from Shopify.
3.  Optionally, select a "Start Date" and "End Date" to filter orders by their fulfillment date. If no dates are selected, all fulfilled orders from the file will be processed.
4.  Check or change the tariff values (in BGN) in the corresponding fields.
5.  Click the "Calculate" button.
6.  The calculation results will appear below, showing summary totals and a detailed table of the processed orders.
7.  You can type in the "Filter by Order #" box to quickly search for specific orders in the results table.
