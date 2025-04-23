from flask import Flask, render_template
import pandas as pd

app = Flask(__name__)

@app.route('/')
def home():
    df = pd.read_excel('data/stock.xlsx')
    products = df.to_dict(orient='records')  # This includes the new Category column
    return render_template('index.html', products=products)

@app.route('/invoice')
def invoice():
    df = pd.read_excel('data/stock.xlsx')
    products = df[df['Stock'] > 0].to_dict(orient='records')  # Only products with stock > 0
    return render_template('invoice.html', products=products)

@app.route('/how_order')
def how_order():
    return render_template('how_order.html')

app = app

if __name__ == '__main__':
    app.run(debug=True)