import os
import uuid
import requests
from flask import Flask, render_template, request, jsonify
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

WEBHOOK_URL = os.environ.get('GOOGLE_SHEETS_WEBHOOK')   # set in Render / .env
WEBHOOK_SECRET = os.environ.get('GOOGLE_SHEETS_SECRET') # set in Render / .env

app = Flask(__name__)

@app.route('/')
def home():
    df = pd.read_excel('data/stock.xlsx')
    products = df.to_dict(orient='records')
    # Extract all unique categories
    categories = set()
    for prod in products:
        if 'Category' in prod and prod['Category']:
            for cat in [c.strip() for c in str(prod['Category']).split(',')]:
                categories.add(cat)
    categories = sorted(categories)
    slides = [f"slide{i}.jpg" for i in range(1, 7)]
    return render_template('index.html', products=products, slides=slides, categories=categories)

@app.route('/invoice')
def invoice():
    df = pd.read_excel('data/stock.xlsx')
    products = df[df['Stock'] > 0].to_dict(orient='records')
    # Extract all unique categories
    categories = set()
    for prod in products:
        if 'Category' in prod and prod['Category']:
            for cat in [c.strip() for c in str(prod['Category']).split(',')]:
                categories.add(cat)
    categories = sorted(categories)
    return render_template('invoice.html', products=products, categories=categories)

@app.route('/how_order')
def how_order():
    return render_template('how_order.html')

@app.route('/pre_order')
def pre_order():
    df = pd.read_excel('data/pre_order.xlsx')
    if 'Category' in df.columns:
        # Split and flatten all categories
        categories = set()
        for cats in df['Category'].dropna():
            for cat in [c.strip() for c in cats.split(',')]:
                categories.add(cat)
        categories = sorted(categories)
    else:
        categories = []
    return render_template('pre_order.html', categories=categories, products=None, selected_category=None)

@app.route('/pre_order/<category>')
def pre_order_category(category):
    df = pd.read_excel('data/pre_order.xlsx')
    if 'Category' in df.columns:
        categories = df['Category'].drop_duplicates().tolist()
        # Show products where the category is in the comma-separated list
        products = df[df['Category'].str.contains(rf'\b{category}\b', case=False, na=False)].to_dict(orient='records')
    else:
        categories = []
        products = []
    return render_template('pre_order.html', categories=categories, products=products, selected_category=category)

from flask import request, jsonify
import smtplib
from email.mime.text import MIMEText

@app.route('/confirm_order', methods=['POST'])
def confirm_order():
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No JSON body'}), 400

    # compute total defensively
    try:
        items = data.get('items', [])
        total = sum(float(item.get('price', 0)) * int(item.get('quantity', 0)) for item in items)
        delivery_charge = float(data.get('deliveryCharge', 0) or 0)
        total += delivery_charge
    except Exception:
        total = data.get('total', 0)

    order_id = data.get('orderId') or str(uuid.uuid4())

    # Format items as a list, one per line (just product name)
    items_str = "\n".join([f"{item.get('name', '')} x{item.get('quantity', 1)} (৳{item.get('price', 0)})" for item in items])

    payload = {
        "secret": WEBHOOK_SECRET,
        "orderId": order_id,
        "customerName": data.get('customerName'),
        "customerPhone": data.get('customerPhone'),
        "customerAddress": data.get('customerAddress'),
        "deliveryArea": data.get('deliveryArea'),
        "deliveryCharge": data.get('deliveryCharge'),
        "customerFB": data.get('customerFB'),
        "customerInsta": data.get('customerInsta'),
        "customerWA": data.get('customerWA'),
        "items": items_str,  # Each item on its own line
        "total": total
    }

    try:
        resp = requests.post(WEBHOOK_URL, json=payload, timeout=10)
        if resp.ok:
            return jsonify({'success': True})
        else:
            print("GSheet webhook failed:", resp.status_code, resp.text)
            return jsonify({'success': False, 'error': 'Webhook responded ' + str(resp.status_code)}), 500
    except Exception as e:
        print("Exception sending to GSheet webhook:", e)
        return jsonify({'success': False, 'error': str(e)}), 500

app = app

if __name__ == '__main__':
    app.run(debug=True)