import os
import uuid
import requests
import json
from flask import Flask, render_template, request, jsonify, send_from_directory, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import pandas as pd
from dotenv import load_dotenv
import gspread
from google.oauth2.service_account import Credentials
import cloudinary
import cloudinary.uploader

load_dotenv()

# Existing env vars
WEBHOOK_URL = os.environ.get('GOOGLE_SHEETS_WEBHOOK')
WEBHOOK_SECRET = os.environ.get('GOOGLE_SHEETS_SECRET')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD')
SECRET_KEY = os.environ.get('SECRET_KEY')

# New env vars for Sheets and Cloudinary
GOOGLE_SHEETS_CREDENTIALS_FILE = os.environ.get('GOOGLE_SHEETS_CREDENTIALS_FILE')
GOOGLE_SHEETS_PRODUCTS_SHEET_ID = os.environ.get('GOOGLE_SHEETS_PRODUCTS_SHEET_ID')
CLOUDINARY_CLOUD_NAME = os.environ.get('CLOUDINARY_CLOUD_NAME')
CLOUDINARY_API_KEY = os.environ.get('CLOUDINARY_API_KEY')
CLOUDINARY_API_SECRET = os.environ.get('CLOUDINARY_API_SECRET')

app = Flask(__name__)
app.secret_key = SECRET_KEY

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'admin_login'

class User(UserMixin):
    def __init__(self, id):
        self.id = id

@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

# Google Sheets setup
with open(os.environ.get('GOOGLE_SHEETS_CREDENTIALS_FILE'), 'r') as f:
    creds_dict = json.load(f)
creds = Credentials.from_service_account_info(creds_dict, scopes=['https://www.googleapis.com/auth/spreadsheets'])
gc = gspread.authorize(creds)
sheet = gc.open_by_key(GOOGLE_SHEETS_PRODUCTS_SHEET_ID).sheet1  # Assumes first sheet

# Cloudinary setup
cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET
)

def get_products():
    records = sheet.get_all_records()
    return records

def update_sheet(products):
    """Update Google Sheet efficiently using batch operations"""
    if not products:
        sheet.clear()
        return

    headers = list(products[0].keys())
    current_data = sheet.get_all_values()

    # If headers changed or sheet is empty, do full rewrite
    if not current_data or current_data[0] != headers:
        sheet.clear()
        sheet.append_row(headers)
        for prod in products:
            sheet.append_row([prod.get(h, '') for h in headers])
        return

    # For data updates, use batch update to minimize API calls
    try:
        # Prepare data rows
        data_rows = [[prod.get(h, '') for h in headers] for prod in products]

        # Use batch update for better performance
        sheet.update(f'A2:{chr(65 + len(headers) - 1)}{len(data_rows) + 1}', data_rows)
    except Exception as e:
        # Fallback to individual appends if batch update fails
        print(f"Batch update failed: {e}, falling back to individual updates")

        # Clear existing data rows
        if len(current_data) > 1:
            sheet.delete_rows(2, len(current_data))

        # Append new data rows
        for row in data_rows:
            sheet.append_row(row)

@app.route('/')
def home():
    products = get_products()
    categories = set()
    for prod in products:
        if 'Category' in prod and prod['Category']:
            for cat in str(prod['Category']).split(','):
                categories.add(cat.strip())
    categories = sorted(categories)
    slides = [f"slide{i}.jpg" for i in range(1, 7)]
    return render_template('index.html', products=products, slides=slides, categories=categories)

@app.route('/invoice')
def invoice():
    products = [p for p in get_products() if int(p.get('Stock', 0)) > 0]
    categories = set()
    for prod in products:
        if 'Category' in prod and prod['Category']:
            for cat in str(prod['Category']).split(','):
                categories.add(cat.strip())
    categories = sorted(categories)
    return render_template('invoice.html', products=products, categories=categories)

@app.route('/how_order')
def how_order():
    return render_template('how_order.html')

@app.route("/sitemap.xml")
def sitemap():
    return send_from_directory("static", "sitemap.xml")

@app.route("/robots.txt")
def robots():
    return send_from_directory("static", "robots.txt")

# Admin routes
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == ADMIN_PASSWORD:
            user = User('admin')
            login_user(user)
            return redirect(url_for('admin_dashboard'))
        flash('Invalid password')
    return render_template('admin_login.html')

@app.route('/admin/logout')
@login_required
def admin_logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/admin')
@login_required
def admin_dashboard():
    products = get_products()
    return render_template('admin_dashboard.html', products=products)

@app.route('/admin/products')
@login_required
def admin_products():
    products = get_products()
    return render_template('admin_products.html', products=products)

@app.route('/admin/api/products', methods=['GET', 'POST'])
@login_required
def api_products():
    if request.method == 'GET':
        products = get_products()
        return jsonify(products)
    elif request.method == 'POST':
        data = request.json
        products = get_products()
        new_id = max([p.get('id', 0) for p in products] or [0]) + 1
        data['id'] = new_id
        products.append(data)
        update_sheet(products)
        return jsonify({'success': True})

@app.route('/admin/api/products/<int:product_id>', methods=['PUT', 'DELETE'])
@login_required
def api_product(product_id):
    products = get_products()
    product = next((p for p in products if p.get('id') == product_id), None)
    if not product:
        return jsonify({'error': 'Product not found'}), 404
    
    if request.method == 'PUT':
        data = request.json
        product.update(data)
        update_sheet(products)
        return jsonify({'success': True})
    elif request.method == 'DELETE':
        products.remove(product)
        update_sheet(products)
        return jsonify({'success': True})

@app.route('/admin/upload_image', methods=['POST'])
@login_required
def upload_image():
    if 'image' not in request.files:
        return jsonify({'error': 'No image file'}), 400
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    upload_result = cloudinary.uploader.upload(file)
    image_url = upload_result['secure_url']
    return jsonify({'image_url': image_url})

@app.route('/confirm_order', methods=['POST'])
def confirm_order():
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No JSON body'}), 400

    try:
        items = data.get('items', [])
        total = sum(float(item.get('price', 0)) * int(item.get('quantity', 0)) for item in items)
        delivery_charge = float(data.get('deliveryCharge', 0) or 0)
        keyring_charge = float(data.get('keyringCharge', 0) or 0)
        total += delivery_charge + keyring_charge
    except Exception:
        total = data.get('total', 0)

    order_id = data.get('orderId') or str(uuid.uuid4())

    items_str = "\n".join([
        f"{item.get('name', '')} x{item.get('quantity', 1)} (৳{item.get('price', 0)})" + 
        (f" + Keyring" if item.get('keyring', False) else "")
        for item in items
    ])

    keyrings_str = ""
    for item in items:
        if 'keyrings' in item and item['keyrings']:
            keyring_units = [f"Unit {i+1}" for i, has_kr in enumerate(item['keyrings']) if has_kr]
            if keyring_units:
                keyrings_str += f"{item['name']}: {', '.join(keyring_units)}\n"
    keyrings_str = keyrings_str.strip()

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
        "items": items_str,
        "total": total,
        "keyringCharge": data.get('keyringCharge', 0),
        "keyringItems": keyrings_str,
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

if __name__ == '__main__':
    app.run(debug=True)