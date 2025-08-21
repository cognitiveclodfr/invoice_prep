import pandas as pd
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

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
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid tariff values'}), 400

    try:
        df = pd.read_csv(file)

        required_columns = ['Fulfillment Status', 'Name', 'Lineitem quantity', 'Lineitem sku']
        for col in required_columns:
            if col not in df.columns:
                return jsonify({'error': f'Missing required column: {col}'}), 400

        fulfilled_df = df[df['Fulfillment Status'] == 'fulfilled'].copy()

        if fulfilled_df.empty:
            return jsonify({
                'processed_orders': 0,
                'total_units': 0,
                'total_cost': 0.0
            })

        orders = fulfilled_df.groupby('Name')

        total_cost = 0
        total_units = 0
        processed_orders = 0

        for order_name, order_group in orders:
            processed_orders += 1

            unique_skus = order_group['Lineitem sku'].nunique()
            order_units = order_group['Lineitem quantity'].sum()

            total_units += order_units

            order_cost = 0
            if unique_skus > 0:
                order_cost += first_sku_cost
            if unique_skus > 1:
                order_cost += (unique_skus - 1) * next_sku_cost

            order_cost += order_units * unit_cost
            total_cost += order_cost

        return jsonify({
            'processed_orders': processed_orders,
            'total_units': int(total_units),
            'total_cost': round(total_cost, 2)
        })

    except Exception as e:
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
