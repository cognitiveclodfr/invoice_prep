import pandas as pd
from flask import Flask, jsonify, render_template, request
from datetime import datetime

app = Flask(__name__)

EUR_TO_BGN_RATE = 1.95583

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/calculate', methods=['POST'])
def calculate():
    if 'csv_file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['csv_file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    try:
        first_sku_cost = float(request.form.get('first_sku_cost', 10.0))
        next_sku_cost = float(request.form.get('next_sku_cost', 5.0))
        unit_cost = float(request.form.get('unit_cost', 2.0))
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid tariff or date values'}), 400

    try:
        df = pd.read_csv(file)

        required_columns = ['Fulfillment Status', 'Name', 'Lineitem quantity', 'Lineitem sku', 'Fulfilled at']
        for col in required_columns:
            if col not in df.columns:
                return jsonify({'error': f'Missing required column: {col}'}), 400

        fulfilled_df = df[df['Fulfillment Status'] == 'fulfilled'].copy()

        # Handle date filtering
        if start_date_str and end_date_str:
            fulfilled_df['Fulfilled at'] = pd.to_datetime(fulfilled_df['Fulfilled at'], errors='coerce')
            fulfilled_df = fulfilled_df.dropna(subset=['Fulfilled at']) # Drop rows where date conversion failed
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
            fulfilled_df = fulfilled_df[(fulfilled_df['Fulfilled at'] >= start_date) & (fulfilled_df['Fulfilled at'] <= end_date)]

        if fulfilled_df.empty:
            return jsonify({
                'processed_orders_count': 0,
                'total_units': 0,
                'total_cost_bgn': 0.0,
                'total_cost_eur': 0.0,
                'orders': []
            })

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

        return jsonify({
            'processed_orders_count': len(processed_orders_list),
            'total_units': int(total_units),
            'total_cost_bgn': round(total_cost_bgn, 2),
            'total_cost_eur': round(total_cost_eur, 2),
            'orders': processed_orders_list
        })

    except Exception as e:
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
