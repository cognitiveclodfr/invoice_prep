import pandas as pd
from datetime import datetime

# Default service SKUs to always exclude
VIRTUAL_SKUS_TO_EXCLUDE = ['parcel-protection']

def calculate_costs(filepath, first_sku_cost, next_sku_cost, unit_cost, eur_to_bgn_rate,
                    start_date_str=None, end_date_str=None, excluded_skus=None):
    """
    Processes a Shopify CSV file to calculate fulfillment costs.
    Applies all filters sequentially before performing calculations.
    """
    if excluded_skus is None:
        excluded_skus = []

    try:
        df = pd.read_csv(filepath)

        required_columns = ['Fulfillment Status', 'Name', 'Lineitem quantity', 'Lineitem sku', 'Lineitem name', 'Fulfilled at']
        for col in required_columns:
            if col not in df.columns:
                return {'error': f'Missing required column: {col}'}

        # --- Sequentially build the filtered DataFrame ---

        # 1. Filter by status
        processed_df = df[df['Fulfillment Status'] == 'fulfilled'].copy()

        # 2. Filter by date range (if provided)
        if start_date_str and end_date_str:
            processed_df['Fulfilled at'] = pd.to_datetime(processed_df['Fulfilled at'], errors='coerce')
            processed_df.dropna(subset=['Fulfilled at'], inplace=True)

            if pd.api.types.is_datetime64_any_dtype(processed_df['Fulfilled at']):
                if processed_df['Fulfilled at'].dt.tz is not None:
                    processed_df['Fulfilled at'] = processed_df['Fulfilled at'].dt.tz_localize(None)

                start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59)

                # Apply the date filter directly to the DataFrame
                processed_df = processed_df[
                    (processed_df['Fulfilled at'] >= start_date) &
                    (processed_df['Fulfilled at'] <= end_date)
                ].copy()

        # 3. Combine and filter by excluded SKUs
        final_excluded_skus = excluded_skus + VIRTUAL_SKUS_TO_EXCLUDE
        if final_excluded_skus:
            processed_df = processed_df[~processed_df['Lineitem sku'].isin(final_excluded_skus)]

        # --- All filters applied. Now perform calculations on the final processed_df ---
        if processed_df.empty:
            return {'totals': {'processed_orders_count': 0, 'total_units': 0, 'total_cost_bgn': 0.0, 'total_cost_eur': 0.0},
                    'order_summary_df': pd.DataFrame(),
                    'line_item_df': pd.DataFrame(),
                    'error': None}

        # --- Calculations ---
        order_summaries = []
        for order_name, order_group in processed_df.groupby('Name'):
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

        order_summary_df = pd.DataFrame(order_summaries) if order_summaries else pd.DataFrame()

        # --- Final Data Preparation ---
        total_cost_bgn = order_summary_df['Order Cost (BGN)'].sum() if not order_summary_df.empty else 0
        total_units = order_summary_df['Total Units'].sum() if not order_summary_df.empty else 0
        final_order_count = processed_df['Name'].nunique()

        totals = {
            'processed_orders_count': final_order_count,
            'total_units': int(total_units),
            'total_cost_bgn': round(total_cost_bgn, 2),
            'total_cost_eur': round(total_cost_bgn / eur_to_bgn_rate, 2) if eur_to_bgn_rate else 0
        }

        line_item_df = processed_df[['Name', 'Fulfilled at', 'Lineitem sku', 'Lineitem name', 'Lineitem quantity']].copy()
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
