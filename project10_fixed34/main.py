from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "farm_secret_key"

def customers_db():
    conn = sqlite3.connect('customers.db')
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            surname TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            phone_number TEXT NOT NULL,
            password TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS producers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            surname TEXT NOT NULL,
            email TEXT NOT NULL,
            phone_number TEXT NOT NULL,
            password TEXT NOT NULL,
            location TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS prdoucts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producer_id INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            product_weight TEXT NOT NULL,
            product_price REAL NOT NULL,
            product_info TEXT NOT NULL,
            image_url TEXT NOT NULL,
            stock INTEGER DEFAULT 0,
            FOREIGN KEY (producer_id) REFERENCES producers(id)
        )
    """)
    # migration: add stock column if it doesn't exist yet
    try:
        cursor.execute("ALTER TABLE prdoucts ADD COLUMN stock INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass  # column already exists

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            order_type TEXT NOT NULL,
            address_line_1 TEXT,
            address_line_2 TEXT,
            town_city TEXT,
            postcode TEXT,
            total_price REAL NOT NULL,
            order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'Pending',
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            product_price REAL NOT NULL,
            quantity INTEGER NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders(id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS contact (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            issue TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

customers_db()

def get_db_connection():
    conn = sqlite3.connect('customers.db')
    conn.row_factory = sqlite3.Row
    return conn


@app.route('/')
def home():
    return render_template('home.html')


@app.route('/products')
def products():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM prdoucts ORDER BY id DESC")
    products = cursor.fetchall()
    conn.close()
    return render_template('products.html', products=products)


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form['name']
        issue = request.form['issue']
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO contact (name, issue) VALUES (?, ?)", (name, issue))
            conn.commit()
            conn.close()
            return render_template('thank.html')
        except sqlite3.Error:
            return "Couldn't take your issue"
    return render_template('contact.html')


@app.route('/weather')
def weather():
    return render_template('weather.html')


@app.route('/privacy')
def privacy():
    return render_template('privacy.html')


@app.route('/cookie_policy')
def cookie():
    return render_template('cookie.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM customers WHERE email = ?", (email,))
        user = cursor.fetchone()
        conn.close()
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['user_name'] = user['first_name']
            session['role'] = 'customer'
            next_page = request.args.get('next')
            return redirect(next_page if next_page else url_for('home'))
        flash("Invalid email or password", "error")
    return render_template('login.html')


@app.route('/registar', methods=['GET', 'POST'])
def registar():
    if request.method == 'POST':
        first_name = request.form['first_name']
        surname = request.form['surname']
        email = request.form['email']
        phone_number = request.form['phone']
        password = request.form['password']
        hashed_password = generate_password_hash(password)
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO customers (first_name, surname, email, phone_number, password)
                VALUES (?, ?, ?, ?, ?)
            """, (first_name, surname, email, phone_number, hashed_password))
            conn.commit()
            conn.close()
            flash("Registration successful! Please log in.", "success")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash("Email already exists", "error")
            return render_template('registar.html', first_name=first_name, surname=surname, email=email, phone=phone_number)
    return render_template('registar.html')


@app.route('/producer_login', methods=['GET', 'POST'])
def prooducer():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM producers WHERE email = ?", (email,))
        user = cursor.fetchone()
        conn.close()
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['user_name'] = user['first_name']
            session['role'] = 'producer'
            return redirect(url_for('dashboard'))
        flash("Invalid email or password", "error")
    return render_template('producer.html')


@app.route('/producer_registar', methods=['GET', 'POST'])
def producer_reg():
    if request.method == 'POST':
        first_name = request.form['first_name']
        surname = request.form['surname']
        email = request.form['email']
        phone_number = request.form['phone']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        location = request.form['location']
        special_chars = "!@#$%^&*()_+-={}[]|\\:;\"'<>,.?/~`"
        numbers = "0123456789"
        if password != confirm_password:
            flash("Passwords do not match", "error")
            return render_template('producersignup.html')
        if (sum(char in special_chars for char in password) < 1 or
                not any(char in numbers for char in password) or
                sum(char.isupper() for char in password) < 1 or
                sum(char.islower() for char in password) < 1):
            flash("Password must include at least one capital letter, one number, one special character and one lowercase letter", "error")
            return render_template('producersignup.html')
        hashed_password = generate_password_hash(password)
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO producers (first_name, surname, email, phone_number, password, location)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (first_name, surname, email, phone_number, hashed_password, location))
            conn.commit()
            conn.close()
            return redirect(url_for('home'))
        except sqlite3.IntegrityError:
            flash("Email already exists", "error")
    return render_template('producersignup.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))


@app.route('/user_details')
def user_details():
    if 'user_id' not in session:
        flash("Access denied", 'error')
        return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor()
    role = session.get('role')
    if role == 'customer':
        cursor.execute("SELECT * FROM customers WHERE id = ?", (session['user_id'],))
    elif role == 'producer':
        cursor.execute("SELECT * FROM producers WHERE id = ?", (session['user_id'],))
    else:
        conn.close()
        return redirect(url_for('login'))
    user = cursor.fetchone()
    conn.close()
    if not user:
        flash(f"{role.capitalize()} not found", "error")
        return redirect(url_for('home'))
    return render_template('user_details.html', user=user, role=role)


@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session or session.get('role') != 'producer':
        flash("Access denied. Producers only.", "error")
        return redirect(url_for('prooducer'))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM prdoucts WHERE producer_id = ?", (session['user_id'],))
    products = cursor.fetchall()
    cursor.execute("SELECT location FROM producers WHERE id = ?", (session['user_id'],))
    producer = cursor.fetchone()
    conn.close()
    producer_location = producer['location'] if producer else 'N/A'
    return render_template('dashboard.html', products=products, product_count=len(products), producer_location=producer_location)


@app.route('/add_product', methods=['GET', 'POST'])
def add_product():
    if 'user_id' not in session or session.get('role') != 'producer':
        flash("You must be logged in as a producer to add products.", "error")
        return redirect(url_for('login'))
    if request.method == 'POST':
        product_name = request.form['product_name']
        product_weight = request.form['product_weight']
        product_price = float(request.form['product_price'])
        product_info = request.form['product_info']
        image_url = request.form['image_url']
        stock = int(request.form['stock'])
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO prdoucts (producer_id, product_name, product_weight, product_price, product_info, image_url, stock)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (session['user_id'], product_name, product_weight, product_price, product_info, image_url, stock))
            conn.commit()
            conn.close()
            flash("Product added successfully!", "success")
            return redirect(url_for('my_products'))
        except sqlite3.Error as e:
            flash(f"Error adding product: {e}", "error")
    return render_template('add_product.html')


@app.route('/edit-product/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    if 'user_id' not in session or session.get('role') != 'producer':
        flash("Access denied", "error")
        return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM prdoucts WHERE id = ? AND producer_id = ?", (product_id, session['user_id']))
    product = cursor.fetchone()
    if not product:
        conn.close()
        flash("Product not found or access denied", "error")
        return redirect(url_for('my_products'))
    if request.method == 'POST':
        product_name = request.form['product_name']
        product_weight = request.form['product_weight']
        product_price = float(request.form['product_price'])
        product_info = request.form['product_info']
        image_url = request.form['image_url']
        stock = int(request.form['stock'])
        cursor.execute("""
            UPDATE prdoucts
            SET product_name=?, product_weight=?, product_price=?, product_info=?, image_url=?, stock=?
            WHERE id=? AND producer_id=?
        """, (product_name, product_weight, product_price, product_info, image_url, stock, product_id, session['user_id']))
        conn.commit()
        conn.close()
        flash("Product updated successfully!", "success")
        return redirect(url_for('my_products'))
    conn.close()
    return render_template('edit_product.html', product=product)


@app.route('/delete-product/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    if 'user_id' not in session or session.get('role') != 'producer':
        flash("Access denied", "error")
        return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM prdoucts WHERE id=? AND producer_id=?", (product_id, session['user_id']))
    conn.commit()
    conn.close()
    flash("Product deleted successfully!", "success")
    return redirect(url_for('my_products'))


@app.route('/my-products')
def my_products():
    if 'user_id' not in session or session.get('role') != 'producer':
        flash("Access denied", "error")
        return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM prdoucts WHERE producer_id=?", (session['user_id'],))
    products = cursor.fetchall()
    conn.close()
    return render_template('my_products.html', products=products)


@app.route('/cart')
def cart():
    if session.get('role') == 'producer':
        flash("Producers cannot access the cart.", "error")
        return redirect(url_for('dashboard'))
    cart_items = session.get('cart', [])
    total = sum(item['price'] * item['quantity'] for item in cart_items)
    return render_template('cart.html', cart_items=cart_items, total=total)


@app.route('/add-to-cart', methods=['POST'])
def add_to_cart():
    product_name = request.form['product_name']
    product_price = float(request.form['product_price'])

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT stock FROM prdoucts WHERE product_name=?", (product_name,))
    row = cursor.fetchone()
    conn.close()

    available_stock = int(row['stock']) if row and row['stock'] is not None else 0

    if 'cart' not in session:
        session['cart'] = []

    cart = list(session['cart'])

    found = False
    for item in cart:
        if item['name'] == product_name:
            found = True
            if item['quantity'] >= available_stock:
                flash(f"Sorry, only {available_stock} available in stock.", "error")
                return redirect(url_for('products'))
            item['quantity'] += 1
            break

    if not found:
        if available_stock < 1:
            flash("This product is out of stock.", "error")
            return redirect(url_for('products'))
        cart.append({'name': product_name, 'price': product_price, 'quantity': 1})

    session['cart'] = cart
    session.modified = True
    return redirect(url_for('products'))


@app.route('/clear-cart')
def clear_cart():
    session.pop('cart', None)
    return redirect(url_for('cart'))


@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if session.get('role') == 'producer':
        flash("Producers cannot checkout.", "error")
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        order_type = request.form['order_type']
        if order_type == 'delivery':
            return redirect(url_for('delivery_details'))
        elif order_type == 'collection':
            return redirect(url_for('collection'))
    return render_template('checkout.html')


@app.route('/delivery-details', methods=['GET', 'POST'])
def delivery_details():
    if 'user_id' not in session:
        return redirect(url_for('login', next=url_for('delivery_details')))
    if request.method == 'POST':
        address_line_1 = request.form['address_line_1']
        address_line_2 = request.form['address_line_2']
        town_city = request.form['town_city']
        postcode = request.form['postcode']
        cart = session.get('cart', [])
        if not cart:
            return redirect(url_for('cart'))
        total_price = sum(item['price'] * item['quantity'] for item in cart)
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO orders (customer_id, order_type, address_line_1, address_line_2, town_city, postcode, total_price)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (session['user_id'], 'Delivery', address_line_1, address_line_2, town_city, postcode, total_price))
        order_id = cursor.lastrowid
        for item in cart:
            cursor.execute("""
                INSERT INTO order_items (order_id, product_name, product_price, quantity)
                VALUES (?, ?, ?, ?)
            """, (order_id, item['name'], item['price'], item['quantity']))
            cursor.execute("""
                UPDATE prdoucts SET stock = stock - ? WHERE product_name = ?
            """, (item['quantity'], item['name']))
        conn.commit()
        conn.close()
        session.pop('cart', None)
        return render_template('delivery_success.html',
            address_line_1=address_line_1, address_line_2=address_line_2,
            town_city=town_city, postcode=postcode)
    return render_template('delivery.html')


@app.route('/collection')
def collection():
    if 'user_id' not in session:
        return redirect(url_for('login', next=url_for('collection')))
    cart = session.get('cart', [])
    if not cart:
        return redirect(url_for('cart'))
    total_price = sum(item['price'] * item['quantity'] for item in cart)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO orders (customer_id, order_type, total_price)
        VALUES (?, ?, ?)
    """, (session['user_id'], 'Collection', total_price))
    order_id = cursor.lastrowid
    for item in cart:
        cursor.execute("""
            INSERT INTO order_items (order_id, product_name, product_price, quantity)
            VALUES (?, ?, ?, ?)
        """, (order_id, item['name'], item['price'], item['quantity']))
        cursor.execute("""
            UPDATE prdoucts SET stock = stock - ? WHERE product_name = ?
        """, (item['quantity'], item['name']))
    conn.commit()
    conn.close()
    session.pop('cart', None)
    return render_template('collection.html')


@app.route('/orders')
def orders():
    if 'user_id' not in session:
        return redirect(url_for('login', next=url_for('orders')))
    if session.get('role') != 'customer':
        flash("Access denied.", "error")
        return redirect(url_for('dashboard'))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders WHERE customer_id=? ORDER BY order_date DESC", (session['user_id'],))
    orders = cursor.fetchall()
    conn.close()
    return render_template('orders.html', orders=orders)


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
