import pandas as pd
from datetime import datetime

EUR_TO_BGN_RATE = 1.95583

def calculate_costs(filepath, first_sku_cost, next_sku_cost, unit_cost, start_date_str=None, end_date_str=None):
    """
    Processes a Shopify CSV file to calculate fulfillment costs.
    """
    try:
        df = pd.read_csv(filepath)

        required_columns = ['Fulfillment Status', 'Name', 'Lineitem quantity', 'Lineitem sku', 'Fulfilled at']
        for col in required_columns:
            if col not in df.columns:
                return {'error': f'Missing required column: {col}'}

        fulfilled_df = df[df['Fulfillment Status'] == 'fulfilled'].copy()

        # Handle date filtering
        if start_date_str and end_date_str:
            fulfilled_df['Fulfilled at'] = pd.to_datetime(fulfilled_df['Fulfilled at'], errors='coerce')
            fulfilled_df = fulfilled_df.dropna(subset=['Fulfilled at'])  # Drop rows where date conversion failed

            # Make the 'Fulfilled at' column timezone-naive to prevent comparison errors
            if pd.api.types.is_datetime64_any_dtype(fulfilled_df['Fulfilled at']) and fulfilled_df['Fulfilled at'].dt.tz is not None:
                fulfilled_df['Fulfilled at'] = fulfilled_df['Fulfilled at'].dt.tz_localize(None)

            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')

            # Add time to end_date to make the range inclusive of the whole day
            end_date = end_date.replace(hour=23, minute=59, second=59)

            fulfilled_df = fulfilled_df[(fulfilled_df['Fulfilled at'] >= start_date) & (fulfilled_df['Fulfilled at'] <= end_date)]

        if fulfilled_df.empty:
            return {
                'processed_orders_count': 0,
                'total_units': 0,
                'total_cost_bgn': 0.0,
                'total_cost_eur': 0.0,
                'orders': []
            }

        orders = fulfilled_df.groupby('Name')

        total_cost_bgn = 0
        total_units = 0
        processed_orders_list = []

        for order_name, order_group in orders:
            unique_skus = order_group['Lineitem sku'].nunique()
            order_units = order_group['Lineitem quantity'].sum()

            total_units += order_units

            order_cost_bgn = 0
            if unique_skus > 0:
                order_cost_bgn += first_sku_cost
            if unique_skus > 1:
                order_cost_bgn += (unique_skus - 1) * next_sku_cost

            order_cost_bgn += order_units * unit_cost
            total_cost_bgn += order_cost_bgn

            processed_orders_list.append({
                'name': order_name,
                'unique_skus': unique_skus,
                'units': int(order_units),
                'cost_bgn': round(order_cost_bgn, 2)
            })

        total_cost_eur = total_cost_bgn / EUR_TO_BGN_RATE

        return {
            'processed_orders_count': len(processed_orders_list),
            'total_units': int(total_units),
            'total_cost_bgn': round(total_cost_bgn, 2),
            'total_cost_eur': round(total_cost_eur, 2),
            'orders': processed_orders_list,
            'error': None
        }

    except FileNotFoundError:
        return {'error': 'The specified file was not found.'}
    except Exception as e:
        return {'error': f'An unexpected error occurred: {str(e)}'}
