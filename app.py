from flask import Flask, render_template
import pandas as pd

app = Flask(__name__)

@app.route('/')
def home():
    df = pd.read_excel('data/stock.xlsx')
    products = df.to_dict(orient='records')  # This includes the new Category column
    slides = [f"slide{i}.jpg" for i in range(1, 7)]
    return render_template('index.html', products=products, slides=slides)

@app.route('/invoice')
def invoice():
    df = pd.read_excel('data/stock.xlsx')
    products = df[df['Stock'] > 0].to_dict(orient='records')  # Only products with stock > 0
    return render_template('invoice.html', products=products)

@app.route('/how_order')
def how_order():
    return render_template('how_order.html')

@app.route('/pre_order')
def pre_order():
    df = pd.read_excel('data/pre_order.xlsx')
    if 'Category' in df.columns:
        categories = df['Category'].drop_duplicates().tolist()
    else:
        categories = []
    return render_template('pre_order.html', categories=categories, products=None, selected_category=None)

@app.route('/pre_order/<category>')
def pre_order_category(category):
    df = pd.read_excel('data/pre_order.xlsx')
    if 'Category' in df.columns:
        categories = df['Category'].drop_duplicates().tolist()
        products = df[df['Category'] == category].to_dict(orient='records')
    else:
        categories = []
        products = []
    return render_template('pre_order.html', categories=categories, products=products, selected_category=category)

app = app

if __name__ == '__main__':
    app.run(debug=True)