"""
GLH WEBSITE
Version: 5.1
DATE: 01/04/2026
Author: HOSSAM EBRAHIM

Changes:
- Integrated OpenWeather API: Added a new /weather route allowing users to check real-time weather conditions via city search.
- Implemented Customer Loyalty Program: Added a 'points' system to the database. Users now earn 1 point for every £1 spent.
- Dynamic Discount Logic: Integrated automatic tiered discounts (5%, 10%, or 20%) during checkout based on the user's accumulated points.
- Enhanced Database Schema: Updated 'customers' table to support point persistence.
- Refined Checkout Flow: Updated both /delivery and /collection routes to calculate discounts, update final totals, and award points upon successful orders.
- UI Expansion: Added weather lookup functionality to the front-end and displayed point balances on the user /account page.
- Code Cleanup: Finalized application startup block with app.run(debug=True) for easier local development.
"""

from flask import Flask, render_template, request, redirect, session, url_for
import sqlite3
import requests
from werkzeug.security import generate_password_hash, check_password_hash
from collections import Counter

app = Flask(__name__)
app.secret_key = 'secret123'


# =========================
# DATABASE SETUP
# =========================

def create_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    # creating table for the customers
    cursor.execute('''CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        first_name TEXT NOT NULL,
        surname TEXT NOT NULL,
        phone TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        points INTEGER DEFAULT 0
    )''')

    # creating table for the products
    cursor.execute('''CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_name TEXT NOT NULL,
        weight INTEGER NOT NULL,
        price REAL NOT NULL,
        description TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        producer_id INTEGER,
        image_url TEXT
    )''')

    # creating table for producers
    cursor.execute('''CREATE TABLE IF NOT EXISTS producers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        first_name TEXT NOT NULL,
        surname TEXT NOT NULL,
        phone TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        area TEXT NOT NULL,
        city TEXT NOT NULL
    )''')

    # creating table for address
    cursor.execute('''CREATE TABLE IF NOT EXISTS address (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        address1 TEXT NOT NULL,
        address2 TEXT,
        city TEXT NOT NULL,
        postcode TEXT NOT NULL
    )''')

    # creating table for orders
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            order_type TEXT,
            address1 TEXT,
            address2 TEXT,
            city TEXT,
            postcode TEXT,
            total REAL,
            status TEXT DEFAULT 'Pending',
            delivery_date TEXT
        )
    ''')

    # creating table for order_items
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER,
            product_id INTEGER,
            quantity INTEGER
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS contact_us (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT NOT NULL,
            subject TEXT NOT NULL,
            massage TEXT NOT NULL
        )
    ''')

    conn.commit()
    conn.close()


########
# WEBSITE ROUTES
#########

@app.route('/')
def home():
    return render_template('home.html')


@app.route('/products')
def products():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()
    conn.close()
    return render_template('products.html', products=products)


@app.route('/cart')
def cart():
    # if user is not logged in will be directed to the login page
    if 'user_id' not in session:
        return redirect('/login')

    cart = session.get('cart', [])
    user_id = session['user_id']

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    # Count how many of each product in the cart
    product_counts = {}
    for p_id in cart:
        product_counts[p_id] = product_counts.get(p_id, 0) + 1

    # Get product details
    products = []
    for product_id, quantity in product_counts.items():
        cursor.execute(
            "SELECT id, product_name, price, description, weight FROM products WHERE id=?",
            (product_id,)
        )
        prod = cursor.fetchone()
        if prod:
            products.append({
                'id': prod[0],
                'product_name': prod[1],
                'price': prod[2],
                'description': prod[3],
                'weight': prod[4],
                'quantity': quantity
            })

    # Calculate total
    total = sum(p['price'] * p['quantity'] for p in products)

    # Get user points
    cursor.execute("SELECT points FROM customers WHERE id=?", (user_id,))
    result = cursor.fetchone()
    points = result[0] if result else 0

    # Discount logic
    def get_discount(points):
        if points >= 500:
            return 0.20
        elif points >= 200:
            return 0.10
        elif points >= 100:
            return 0.05
        return 0

    # Apply discount
    discount = get_discount(points)
    discount_amount = total * discount
    final_total = total - discount_amount

    conn.close()

    return render_template(
        'cart.html',
        products=products,
        total=total,
        points=points,
        discount=discount,
        discount_amount=discount_amount,
        final_total=final_total
    )


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM customers WHERE email=?", (email,))
        user = cursor.fetchone()
        conn.close()

        # check hashed password
        if user and check_password_hash(user[5], password):
            session['user_id'] = user[0]
            session['first_name'] = user[1]
            return redirect(url_for('home'))
        else:
            return "Invalid email or password ❌"

    return render_template('signin.html')


@app.route('/producer_login', methods=['GET', 'POST'])
def producer_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM producers WHERE email=?", (email,))
        producer = cursor.fetchone()
        conn.close()

        if producer and check_password_hash(producer[5], password):
            session['producer_id'] = producer[0]
            session['producer_name'] = producer[1]
            return redirect(url_for('home'))
        else:
            return "Invalid producer login ❌"

    return render_template('producer_login.html')


@app.route('/thanks_contact')
def thanks_contact():
    return render_template('thanks_contact.html')
@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        full_name = request.form['name']
        email = request.form['email']
        subject = request.form['subject']
        message = request.form['message']

        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO contact_us(full_name, email, subject, massage)
            VALUES (?, ?, ?, ?)
        ''', (full_name, email, subject, message))

        conn.commit()
        conn.close()

        return redirect(url_for('thanks_contact'))

    return render_template('contact.html')


@app.route('/producer_register', methods=['GET', 'POST'])
def producer_register():
    if request.method == 'POST':
        first_name = request.form['first_name']
        surname = request.form['surname']
        phone = request.form['phone']
        email = request.form['email']
        password = request.form['password']
        area = request.form['area']
        city = request.form['city']

        hashed_password = generate_password_hash(password)

        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()

        # check if email exists
        cursor.execute("SELECT * FROM producers WHERE email=?", (email,))
        existing = cursor.fetchone()

        if existing:
            conn.close()
            return "Producer already exists ❌"

        cursor.execute('''
            INSERT INTO producers (first_name, surname, phone, email, password, area, city)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (first_name, surname, phone, email, hashed_password, area, city))

        conn.commit()
        conn.close()

        return redirect(url_for('producer_login'))

    return render_template('producer_register.html')


@app.route('/add-product', methods=['GET', 'POST'])
def add_product():
    if 'producer_id' not in session:
        return redirect('/producer_login')

    if request.method == 'POST':
        name = request.form['product_name']
        weight = request.form['weight']
        price = request.form['price']
        description = request.form['description']
        quantity = request.form['quantity']
        producer_id = session['producer_id']
        image_url = request.form['image_url']

        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO products (product_name, weight, price, description, quantity, producer_id, image_url)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (name, weight, price, description, quantity, producer_id, image_url))

        conn.commit()
        conn.close()

        return redirect('/products')

    return render_template('add_product.html')


@app.route('/add-to-cart', methods=['POST'])
def add_to_cart():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    product_id = int(request.form['product_id'])

    # Initialize cart if it doesn't exist
    if 'cart' not in session:
        session['cart'] = []

    cart = session['cart']

    # Get product stock
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT quantity FROM products WHERE id=?", (product_id,))
    result = cursor.fetchone()
    conn.close()

    if not result:
        return "Product not found"

    stock = result[0]

    # Count how many already in cart
    current_count = cart.count(product_id)

    # Check stock first
    if stock == 0:
        return "This product is out of stock"

    # Then check how many already in cart
    if current_count >= stock:
        return f"You can only add {stock} of this product"

    # Add product
    cart.append(product_id)
    session['cart'] = cart
    session.modified = True

    return redirect('/products')


@app.route('/remove-from-cart/<int:product_id>')
def remove_from_cart(product_id):
    cart = session.get('cart', [])

    if product_id in cart:
        cart.remove(product_id)

    session['cart'] = cart
    session.modified = True

    return redirect('/cart')


@app.route('/checkout')
def checkout():
    if 'user_id' not in session:
        return redirect('/login')

    cart = session.get('cart', [])
    user_id = session['user_id']

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    total = 0
    for product_id in cart:
        cursor.execute("SELECT price FROM products WHERE id=?", (product_id,))
        product = cursor.fetchone()
        if product:
            total += product[0]

    # get user points
    cursor.execute("SELECT points FROM customers WHERE id=?", (user_id,))
    result = cursor.fetchone()
    points = result[0] if result else 0

    # discount logic
    def get_discount(points):
        if points >= 500:
            return 0.20
        elif points >= 200:
            return 0.10
        elif points >= 100:
            return 0.05
        return 0

    discount = get_discount(points)
    discount_amount = total * discount
    final_total = total - discount_amount

    conn.close()

    return render_template(
        'checkout.html',
        total=total,
        discount=discount,
        discount_amount=discount_amount,
        final_total=final_total,
        points=points
    )


@app.route('/delivery', methods=['GET', 'POST'])
def delivery():
    if 'user_id' not in session:
        return redirect('/login')

    if request.method == 'POST':
        address1 = request.form['address1']
        address2 = request.form['address2']
        city = request.form['city']
        postcode = request.form['postcode']
        delivery_date = request.form['delivery_date']

        if not address1 or not city or not postcode:
            return "All fields required"

        cart = session.get('cart', [])
        user_id = session['user_id']

        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()

        # CHECK STOCK
        for product_id in cart:
            cursor.execute("SELECT quantity FROM products WHERE id=?", (product_id,))
            stock = cursor.fetchone()
            if not stock or stock[0] <= 0:
                return "One of the products is out of stock"

        # CALCULATE TOTAL
        total = 0
        for product_id in cart:
            cursor.execute("SELECT price FROM products WHERE id=?", (product_id,))
            product = cursor.fetchone()
            if product:
                total += product[0]

        # get user points
        cursor.execute("SELECT points FROM customers WHERE id=?", (user_id,))
        result = cursor.fetchone()
        points = result[0] if result else 0

        # discount logic
        def get_discount(points):
            if points >= 500:
                return 0.20
            elif points >= 200:
                return 0.10
            elif points >= 100:
                return 0.05
            return 0

        discount = get_discount(points)
        discount_amount = total * discount
        final_total = total - discount_amount

        cursor.execute('''
            INSERT INTO orders (user_id, order_type, address1, address2, city, postcode, total, delivery_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, "delivery", address1, address2, city, postcode, final_total, delivery_date))

        order_id = cursor.lastrowid
        points_earned = int(total)

        cursor.execute("""
            UPDATE customers
            SET points = points + ?
            WHERE id=?
        """, (points_earned, user_id))

        for product_id in cart:
            cursor.execute('''
                INSERT INTO order_items (order_id, product_id, quantity)
                VALUES (?, ?, ?)
            ''', (order_id, product_id, 1))

            cursor.execute('''
                UPDATE products
                SET quantity = quantity - 1
                WHERE id=? AND quantity > 0
            ''', (product_id,))

        conn.commit()
        conn.close()

        # clear cart
        session['cart'] = []
        session.modified = True

        return redirect('/thankyou')

    return render_template('delivery.html')


@app.route('/collection')
def collection():
    if 'user_id' not in session:
        return redirect('/login')

    cart = session.get('cart', [])
    user_id = session['user_id']

    if not cart:
        return "Cart is empty"

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    total = 0
    for product_id in cart:
        cursor.execute("SELECT price FROM products WHERE id=?", (product_id,))
        product = cursor.fetchone()
        if product:
            total += product[0]

    # get user points
    cursor.execute("SELECT points FROM customers WHERE id=?", (user_id,))
    result = cursor.fetchone()
    points = result[0] if result else 0

    # discount logic
    def get_discount(points):
        if points >= 500:
            return 0.20
        elif points >= 200:
            return 0.10
        elif points >= 100:
            return 0.05
        return 0

    discount = get_discount(points)
    discount_amount = total * discount
    final_total = total - discount_amount

    cursor.execute('''
        INSERT INTO orders (user_id, order_type, total)
        VALUES (?, ?, ?)
    ''', (user_id, "collection", final_total))

    order_id = cursor.lastrowid
    points_earned = int(total)

    cursor.execute("""
        UPDATE customers
        SET points = points + ?
        WHERE id=?
    """, (points_earned, user_id))

    for product_id in cart:
        cursor.execute('''
            INSERT INTO order_items (order_id, product_id, quantity)
            VALUES (?, ?, ?)
        ''', (order_id, product_id, 1))

        cursor.execute('''
            UPDATE products
            SET quantity = quantity - 1
            WHERE id=? AND quantity > 0
        ''', (product_id,))

    conn.commit()
    conn.close()

    session['cart'] = []
    session.modified = True

    return redirect('/thankyou')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        first_name = request.form['first_name']
        surname = request.form['surname']
        phone = request.form['phone']
        email = request.form['email']
        password = request.form['password']

        hashed_password = generate_password_hash(password)

        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()

        # check if email already exists
        cursor.execute("SELECT * FROM customers WHERE email=?", (email,))
        existing_user = cursor.fetchone()

        if existing_user:
            conn.close()
            return "Email already exists ❌"

        cursor.execute('''
            INSERT INTO customers (first_name, surname, phone, email, password)
            VALUES (?, ?, ?, ?, ?)
        ''', (first_name, surname, phone, email, hashed_password))

        conn.commit()
        conn.close()

        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/process-checkout', methods=['POST'])
def process_checkout():
    method = request.form.get('method')
    print("Selected method:", method)

    if method == 'delivery':
        return redirect('/delivery')
    elif method == 'collection':
        return redirect('/collection')

    return redirect('/checkout')


@app.route('/orders')
def orders():
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, order_type, total, status, delivery_date
        FROM orders
        WHERE user_id=?
        ORDER BY id DESC
    """, (user_id,))
    orders = cursor.fetchall()

    conn.close()
    return render_template('orders.html', orders=orders)


@app.route('/account', methods=['GET', 'POST'])
def account():
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    if request.method == 'POST':
        first_name = request.form.get('first_name')
        surname = request.form.get('surname')
        phone = request.form.get('phone')

        cursor.execute("""
            UPDATE customers
            SET first_name=?, surname=?, phone=?
            WHERE id=?
        """, (first_name, surname, phone, user_id))
        conn.commit()
        session['first_name'] = first_name

    # Always fetch latest user info
    cursor.execute("SELECT first_name, surname, phone, email, points FROM customers WHERE id=?", (user_id,))
    user = cursor.fetchone()
    conn.close()

    if not user:
        return "User not found", 404

    return render_template('account.html', user=user)


@app.route('/producer-account', methods=['GET', 'POST'])
def producer_account():
    if 'producer_id' not in session:
        return redirect('/producer_login')

    producer_id = session['producer_id']

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    if request.method == 'POST':
        first_name = request.form.get('first_name')
        surname = request.form.get('surname')
        phone = request.form.get('phone')
        area = request.form.get('area')
        city = request.form.get('city')

        cursor.execute("""
            UPDATE producers
            SET first_name=?, surname=?, phone=?, area=?, city=?
            WHERE id=?
        """, (first_name, surname, phone, area, city, producer_id))

        conn.commit()
        session['producer_name'] = first_name

    cursor.execute("""
        SELECT first_name, surname, phone, email, area, city
        FROM producers
        WHERE id=?
    """, (producer_id,))
    producer = cursor.fetchone()

    cursor.execute("""
        SELECT * FROM products
        WHERE producer_id=?
    """, (producer_id,))
    products = cursor.fetchall()

    conn.close()

    return render_template('producer_account.html', producer=producer, products=products)


@app.route('/producer-dashboard')
def producer_dashboard():
    if 'producer_id' not in session:
        return redirect('/producer_login')

    producer_id = session['producer_id']

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM products WHERE producer_id=?", (producer_id,))
    products = cursor.fetchall()

    conn.close()

    return render_template('producer_dashboard.html', products=products)


@app.route('/update-stock/<int:product_id>', methods=['POST'])
def update_stock(product_id):
    if 'producer_id' not in session:
        return redirect('/producer_login')

    new_quantity = request.form['quantity']
    producer_id = session['producer_id']

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE products
        SET quantity=?
        WHERE id=? AND producer_id=?
    """, (new_quantity, product_id, producer_id))

    conn.commit()
    conn.close()

    return redirect('/producer-dashboard')


@app.route('/edit-product/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    if 'producer_id' not in session:
        return redirect('/producer_login')

    producer_id = session['producer_id']

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    if request.method == 'POST':
        name = request.form['product_name']
        price = request.form['price']
        description = request.form['description']

        cursor.execute("""
            UPDATE products
            SET product_name=?, price=?, description=?
            WHERE id=? AND producer_id=?
        """, (name, price, description, product_id, producer_id))

        conn.commit()
        conn.close()
        return redirect('/producer-dashboard')

    cursor.execute("""
        SELECT * FROM products
        WHERE id=? AND producer_id=?
    """, (product_id, producer_id))

    product = cursor.fetchone()
    conn.close()

    return render_template('edit_product.html', product=product)


@app.route('/delete-product/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    if 'producer_id' not in session:
        return redirect('/producer_login')

    producer_id = session['producer_id']

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM products
        WHERE id=? AND producer_id=?
    """, (product_id, producer_id))

    conn.commit()
    conn.close()

    return redirect('/producer-dashboard')


@app.route('/producer-orders')
def producer_orders():
    if 'producer_id' not in session:
        return redirect('/producer_login')

    producer_id = session['producer_id']

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    cursor.execute("""
        SELECT orders.id, orders.total, orders.order_type
        FROM orders
        JOIN order_items ON orders.id = order_items.order_id
        JOIN products ON order_items.product_id = products.id
        WHERE products.producer_id=?
        GROUP BY orders.id
        ORDER BY orders.id DESC
    """, (producer_id,))

    orders = cursor.fetchall()
    conn.close()

    return render_template('producer_orders.html', orders=orders)


@app.route('/weather', methods=['GET', 'POST'])
def weather():
    city = None
    weather = None
    error = None

    if request.method == 'POST':
        city = request.form.get('city')

        api_key = "f3eb1ef6c8470a78795004da60ac347e"
        url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"

        response = requests.get(url)
        data = response.json()

        if data.get("cod") != 200:
            error = data.get("message")
        else:
            weather = {
                "city": city,
                "temperature": data["main"]["temp"],
                "description": data["weather"][0]["description"],
                "humidity": data["main"]["humidity"],
                "wind": data["wind"]["speed"]
            }

    return render_template('weather.html', weather=weather, error=error)


@app.route('/order/<int:order_id>')
def order_details(order_id):
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT products.product_name, products.price, SUM(order_items.quantity) AS total_quantity
        FROM order_items
        JOIN products ON order_items.product_id = products.id
        WHERE order_items.order_id=?
        GROUP BY products.id
    """, (order_id,))
    items_raw = cursor.fetchall()

    items = []
    for item in items_raw:
        items.append({
            'product_name': item['product_name'],
            'price': float(item['price']),
            'quantity': item['total_quantity']
        })

    cursor.execute("SELECT * FROM orders WHERE id=?", (order_id,))
    order_row = cursor.fetchone()
    order = dict(order_row) if order_row else None

    conn.close()

    if not order:
        return "Order not found", 404

    return render_template('order_details.html', items=items, order=order)


@app.route('/payment')
def payment():
    return render_template('payment.html')


@app.route('/thankyou')
def thankyou():
    return render_template('thank.html')


@app.route('/privacy')
def privacy():
    return render_template('privacy.html')


@app.route('/cookies')
def cookies():
    return render_template('cookies.html')


# LOGOUT

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))


# =========================
# RUN APP
# =========================
import os
print(os.path.abspath('database.db'))

if __name__ == '__main__':
    create_db()
    app.run(debug=True)
