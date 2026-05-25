"""
    My Farm
    24/03/2026
    Version v1.0
"""
#liparies installed
from flask import Flask, render_template

app = Flask(__name__) #app name

#app routes to get the templates back
@app.route('/')
def home():
    return render_template("home.html")


@app.route('/products')
def products():
    return render_template('products.html')

@app.route('/orders')
def orders():
    return render_template('orders.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/login')
def login():
    return render_template('login.html')


if __name__ == "__main__":
    app.run(debug=True)