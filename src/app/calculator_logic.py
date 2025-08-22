import pandas as pd
from datetime import datetime

def calculate_costs(filepath, first_sku_cost, next_sku_cost, unit_cost,
                    start_date_str=None, end_date_str=None, excluded_skus=None):
    """
    Processes a Shopify CSV file to calculate fulfillment costs based on the new TZ.
    """
    if excluded_skus is None:
        excluded_skus = []

    try:
        df = pd.read_csv(filepath)

        # F1: Check for required columns from TZ
        required_columns = ['Name', 'Fulfilled at', 'Lineitem sku', 'Lineitem quantity']
        for col in required_columns:
            if col not in df.columns:
                return {'error': f'Помилка: у файлі відсутній обов\'язковий стовпець: {col}'}

        # --- Data Cleaning and Filtering ---

        # 1. Handle 'Fulfilled at' date column
        # Convert to datetime, coercing errors will result in NaT (Not a Time)
        df['Fulfilled at'] = pd.to_datetime(df['Fulfilled at'], errors='coerce')
        # F3.1: Ignore orders without a valid fulfillment date
        df.dropna(subset=['Fulfilled at'], inplace=True)

        # Ensure timezone-naive for comparison
        if pd.api.types.is_datetime64_any_dtype(df['Fulfilled at']):
            if df['Fulfilled at'].dt.tz is not None:
                df['Fulfilled at'] = df['Fulfilled at'].dt.tz_localize(None)

        # 2. Filter by date range
        if start_date_str and end_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
            df = df[(df['Fulfilled at'] >= start_date) & (df['Fulfilled at'] <= end_date)].copy()

        # 3. Filter by excluded SKUs (user-provided list only)
        if excluded_skus:
            df = df[~df['Lineitem sku'].isin(excluded_skus)]

        if df.empty:
            return {
                'order_details': [],
                'summary': {
                    'total_orders': 0, 'total_units': 0, 'total_cost': 0.0,
                    'cost_from_first_sku': 0.0, 'cost_from_next_sku': 0.0, 'cost_from_unit': 0.0
                },
                'error': None
            }

        # --- Calculations per Order ---
        order_details = []
        total_summary = {
            'total_orders': 0, 'total_units': 0, 'total_cost': 0.0,
            'cost_from_first_sku': 0.0, 'cost_from_next_sku': 0.0, 'cost_from_unit': 0.0
        }

        # Group by order name ('Name' column)
        for order_name, order_group in df.groupby('Name'):
            # F3.4: Calculate N and Q for the order
            N = order_group['Lineitem sku'].nunique()
            Q = order_group['Lineitem quantity'].sum()

            if N == 0:
                continue # Skip orders that have no SKUs left after filtering

            # F3.5: Apply the calculation formula
            cost_first = 0
            cost_next = 0
            cost_unit = Q * unit_cost

            if N == 1:
                cost_first = first_sku_cost
            elif N > 1:
                cost_first = first_sku_cost
                cost_next = (N - 1) * next_sku_cost

            total_cost = cost_first + cost_next + cost_unit

            order_details.append({
                'Номер замовлення': order_name,
                'Дата виконання': order_group['Fulfilled at'].iloc[0].strftime('%Y-%m-%d'),
                'Кількість SKU': N,
                'Загальна кількість одиниць': int(Q),
                'Підсумкова вартість': round(total_cost, 2)
            })

            # Aggregate summary data
            total_summary['total_orders'] += 1
            total_summary['total_units'] += int(Q)
            total_summary['total_cost'] += total_cost
            total_summary['cost_from_first_sku'] += cost_first
            total_summary['cost_from_next_sku'] += cost_next
            total_summary['cost_from_unit'] += cost_unit

        # Round the final summary costs
        for key in ['total_cost', 'cost_from_first_sku', 'cost_from_next_sku', 'cost_from_unit']:
            total_summary[key] = round(total_summary[key], 2)

        return {
            'order_details': order_details,
            'summary': total_summary,
            'error': None
        }

    except FileNotFoundError:
        return {'error': 'Помилка: вказаний файл не знайдено.'}
    except Exception as e:
        return {'error': f'Виникла неочікувана помилка: {str(e)}'}
