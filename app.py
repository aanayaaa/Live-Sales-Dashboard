import pandas as pd
from flask import Flask, render_template
from flask_socketio import SocketIO, emit

app = Flask(__name__)
socketio = SocketIO(app)

# Load CSV and preprocess
sales_df = pd.read_csv('sales_data.csv')
sales_df['Date'] = pd.to_datetime(sales_df['Date'])

@app.route('/')
def dashboard():
    regions = sorted(sales_df['Region'].dropna().unique())
    categories = sorted(sales_df['Product Category'].dropna().unique())
    products = sorted(sales_df['Product Name'].dropna().unique())
    min_date = sales_df['Date'].min().date().isoformat()
    max_date = sales_df['Date'].max().date().isoformat()
    return render_template('dashboard.html',
                           regions=regions,
                           categories=categories,
                           products=products,
                           min_date=min_date,
                           max_date=max_date)

def prepare_data(region=None, category=None, product=None, start_date=None, end_date=None):
    df = sales_df.copy()

    if region:
        df = df[df['Region'] == region]
    if category:
        df = df[df['Product Category'] == category]
    if product:
        df = df[df['Product Name'] == product]
    if start_date:
        try:
            df = df[df['Date'] >= pd.to_datetime(start_date)]
        except Exception as e:
            print(f"Invalid start date: {start_date}, Error: {e}")
    if end_date:
        try:
            df = df[df['Date'] <= pd.to_datetime(end_date)]
        except Exception as e:
            print(f"Invalid end date: {end_date}, Error: {e}")

    print(f"Filtered rows: {len(df)}")

    total_sales = float(df['Total Revenue'].sum())
    grouped = df.groupby('Product Name')['Total Revenue'].sum()
    top_product = grouped.idxmax() if not grouped.empty else ""
    top_product_sales = float(grouped.max()) if not grouped.empty else 0

    sales_by_region = df.groupby('Region')['Total Revenue'].sum().to_dict()
    sales_by_payment = df.groupby('Payment Method')['Total Revenue'].sum().to_dict()
    top_products_df = grouped.sort_values(ascending=False).head(5)
    top_products = [{'product': idx, 'sales': float(val)} for idx, val in top_products_df.items()]
    sales_trend = df.groupby('Date')['Total Revenue'].sum().sort_index().to_dict()
    category_breakdown = df.groupby('Product Category')['Total Revenue'].sum().to_dict()

    return {
        'total_sales': round(total_sales, 2),
        'top_product': top_product,
        'top_product_sales': round(top_product_sales, 2),
        'sales_by_region': sales_by_region,
        'sales_by_payment': sales_by_payment,
        'top_products': top_products,
        'sales_trend': {k.strftime('%Y-%m-%d'): v for k, v in sales_trend.items()},
        'category_breakdown': category_breakdown
    }

@socketio.on('connect')
def handle_connect():
    print("Client connected")
    emit('update', prepare_data())  # Send initial data on load

@socketio.on('filter')
def handle_filter(filters):
    print("Received filters:", filters)
    data = prepare_data(
        region=filters.get('region'),
        category=filters.get('category'),
        product=filters.get('product'),
        start_date=filters.get('start_date'),
        end_date=filters.get('end_date')
    )
    emit('update', data, broadcast=False)  # Ensure update is sent only to filtering client

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)

