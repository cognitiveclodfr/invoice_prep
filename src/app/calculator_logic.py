import pandas as pd
from datetime import datetime

EUR_TO_BGN_RATE = 1.95583

def calculate_costs(filepath, first_sku_cost, next_sku_cost, unit_cost,
                    start_date_str=None, end_date_str=None, excluded_skus=None):
    """
    Processes a Shopify CSV file to calculate fulfillment costs.
    Returns a dictionary containing detailed results for export and display.
    """
    if excluded_skus is None:
        excluded_skus = []

    try:
        df = pd.read_csv(filepath)

        required_columns = ['Fulfillment Status', 'Name', 'Lineitem quantity', 'Lineitem sku', 'Lineitem name', 'Fulfilled at']
        for col in required_columns:
            if col not in df.columns:
                return {'error': f'Missing required column: {col}'}

        # --- Initial Filtering ---
        fulfilled_df = df[df['Fulfillment Status'] == 'fulfilled'].copy()

        # Filter out excluded SKUs before any calculations
        if excluded_skus:
            fulfilled_df = fulfilled_df[~fulfilled_df['Lineitem sku'].isin(excluded_skus)]

        # --- Date Filtering ---
        if start_date_str and end_date_str:
            date_filtered_df = fulfilled_df.copy()
            date_filtered_df['Fulfilled at'] = pd.to_datetime(date_filtered_df['Fulfilled at'], errors='coerce')
            date_filtered_df.dropna(subset=['Fulfilled at'], inplace=True)

            # Only proceed if the column is a datetime type after coercion
            if pd.api.types.is_datetime64_any_dtype(date_filtered_df['Fulfilled at']):
                if not date_filtered_df.empty:
                    start_date = pd.Timestamp(start_date_str)
                    end_date = pd.Timestamp(end_date_str).replace(hour=23, minute=59, second=59)
                    source_tz = date_filtered_df['Fulfilled at'].dt.tz
                    if source_tz:
                        start_date = start_date.tz_localize(source_tz)
                        end_date = end_date.tz_localize(source_tz)

                    date_filtered_df = date_filtered_df[(date_filtered_df['Fulfilled at'] >= start_date) & (date_filtered_df['Fulfilled at'] <= end_date)]
                    valid_order_names = date_filtered_df['Name'].unique()
                    fulfilled_df = fulfilled_df[fulfilled_df['Name'].isin(valid_order_names)].copy()
                else:
                    # If empty after dropping NaTs, means no valid dates in range
                    fulfilled_df = pd.DataFrame(columns=fulfilled_df.columns)
            else:
                # If the column could not be converted to datetime at all
                fulfilled_df = pd.DataFrame(columns=fulfilled_df.columns)

        if fulfilled_df.empty:
            return {'totals': {'processed_orders_count': 0, 'total_units': 0, 'total_cost_bgn': 0.0, 'total_cost_eur': 0.0},
                    'order_summary_df': pd.DataFrame(),
                    'line_item_df': pd.DataFrame(),
                    'error': None}

        # --- Calculations ---
        order_summaries = []

        for order_name, order_group in fulfilled_df.groupby('Name'):
            unique_skus = order_group['Lineitem sku'].nunique()
            order_units = order_group['Lineitem quantity'].sum()

            order_cost_bgn = 0
            if unique_skus > 0:
                order_cost_bgn += first_sku_cost
            if unique_skus > 1:
                order_cost_bgn += (unique_skus - 1) * next_sku_cost
            order_cost_bgn += order_units * unit_cost

            order_summaries.append({
                'Order #': order_name,
                'Unique SKUs': unique_skus,
                'Total Units': int(order_units),
                'Order Cost (BGN)': round(order_cost_bgn, 2)
            })

        order_summary_df = pd.DataFrame(order_summaries)

        # --- Final Data Preparation ---
        total_cost_bgn = order_summary_df['Order Cost (BGN)'].sum() if not order_summary_df.empty else 0
        total_units = order_summary_df['Total Units'].sum() if not order_summary_df.empty else 0

        totals = {
            'processed_orders_count': len(order_summary_df),
            'total_units': int(total_units),
            'total_cost_bgn': round(total_cost_bgn, 2),
            'total_cost_eur': round(total_cost_bgn / EUR_TO_BGN_RATE, 2)
        }

        # Prepare line item df for display and export
        line_item_df = fulfilled_df[['Name', 'Fulfilled at', 'Lineitem sku', 'Lineitem name', 'Lineitem quantity']].copy()
        line_item_df.rename(columns={
            'Name': 'Order #',
            'Fulfilled at': 'Fulfilled Date',
            'Lineitem sku': 'SKU',
            'Lineitem name': 'Product Name',
            'Lineitem quantity': 'Quantity'
        }, inplace=True)


        return {
            'totals': totals,
            'order_summary_df': order_summary_df,
            'line_item_df': line_item_df,
            'error': None
        }

    except FileNotFoundError:
        return {'error': 'The specified file was not found.'}
    except Exception as e:
        return {'error': f'An unexpected error occurred: {str(e)}'}
