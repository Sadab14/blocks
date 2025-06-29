from flask import Flask, render_template
import pandas as pd

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
    total = sum(item['price'] * item['quantity'] for item in data['items']) + int(data['deliveryCharge'])
    subject = "New Order from BLOCKS"
    body = f"""
    Name: {data['customerName']}
    Phone: {data['customerPhone']}
    Address: {data['customerAddress']}
    Facebook: {data.get('customerFB', '')}
    Instagram: {data.get('customerInsta', '')}
    WhatsApp: {data.get('customerWA', '')}
    Delivery Area: {data['deliveryArea']}
    Delivery Charge: {data['deliveryCharge']}
    Items:
    """
    for item in data['items']:
        body += f"\n- {item['name']} x{item['quantity']} (৳{item['price']})"
    body += f"\n\nTotal: ৳{total}"
    try:
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = 'sadabshakib14@gmail.com'
        msg['To'] = 'blocks.snapthat@gmail.com'
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login('sadabshakib14@gmail.com', 'gwko ngdx fgze aqti')
            server.send_message(msg)
        return jsonify({'success': True})
    except Exception as e:
        print(e)
        return jsonify({'success': False})

app = app

if __name__ == '__main__':
    app.run(debug=True)