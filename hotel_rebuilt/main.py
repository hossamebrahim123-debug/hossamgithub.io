import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import random
import string

app = Flask(__name__)
app.secret_key = "luxury_hotel_secret_key_2026"
DB_NAME = "hotel.db"

ROOM_PRICES = {
    'Deluxe Suite': 199,
    'Presidential Suite': 450
}

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fullname TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            room_type TEXT NOT NULL,
            checkin TEXT NOT NULL,
            checkout TEXT NOT NULL,
            guests INTEGER NOT NULL,
            total_price REAL NOT NULL,
            reference TEXT NOT NULL,
            status TEXT DEFAULT 'Confirmed',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            fullname TEXT NOT NULL,
            rating INTEGER NOT NULL,
            room_type TEXT NOT NULL,
            comment TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()

    # Add sample reviews if empty
    cursor.execute("SELECT COUNT(*) FROM reviews")
    if cursor.fetchone()[0] == 0:
        sample_reviews = [
            (None, 'James & Sarah', 5, 'Presidential Suite', 'Absolutely incredible stay. The suite was stunning and the butler service was second to none. We will definitely be back.', '2026-04-10'),
            (None, 'Michael Thompson', 5, 'Deluxe Suite', 'The room was beautifully decorated and the views of London were breathtaking. Staff were incredibly attentive throughout our stay.', '2026-03-22'),
            (None, 'Amelia Clarke', 4, 'Deluxe Suite', 'A wonderful experience overall. The marble bathroom was a highlight and breakfast was superb. Would highly recommend.', '2026-02-15'),
            (None, 'Robert Hughes', 5, 'Presidential Suite', 'We celebrated our anniversary here and it exceeded every expectation. The attention to detail was remarkable.', '2026-01-30'),
        ]
        cursor.executemany("INSERT INTO reviews (user_id, fullname, rating, room_type, comment, created_at) VALUES (?,?,?,?,?,?)", sample_reviews)
        conn.commit()

    conn.close()

init_db()

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def generate_reference():
    return 'TG-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

def check_availability(room_type, checkin, checkout):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) FROM bookings
        WHERE room_type = ? AND status = 'Confirmed'
        AND NOT (checkout <= ? OR checkin >= ?)
    """, (room_type, checkin, checkout))
    count = cursor.fetchone()[0]
    conn.close()
    return count == 0

@app.route('/')
def home():
    conn = get_db()
    reviews = conn.execute("SELECT * FROM reviews ORDER BY created_at DESC LIMIT 3").fetchall()
    conn.close()
    return render_template('home.html', reviews=reviews)

@app.route('/rooms')
def rooms():
    return render_template('rooms.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/offers')
def offers():
    return render_template('offers.html')

@app.route('/cancellation')
def cancellation():
    return render_template('cancellation.html')

@app.route('/booking', methods=['GET', 'POST'])
def booking():
    if request.method == 'POST':
        room_type = request.form.get('room_type')
        checkin = request.form.get('checkin')
        checkout = request.form.get('checkout')
        guests = request.form.get('guests')

        if not room_type or not checkin or not checkout:
            flash("Please fill in all fields.", "error")
            return render_template('booking.html', room=request.args.get('room', ''))

        # Calculate total
        try:
            ci = datetime.strptime(checkin, '%Y-%m-%d')
            co = datetime.strptime(checkout, '%Y-%m-%d')
            nights = (co - ci).days
            if nights <= 0:
                flash("Check-out must be after check-in.", "error")
                return render_template('booking.html')
        except:
            flash("Invalid dates.", "error")
            return render_template('booking.html')

        # Check availability
        if not check_availability(room_type, checkin, checkout):
            flash(f"Sorry, the {room_type} is not available for those dates. Please try different dates.", "error")
            return render_template('booking.html', room=request.args.get('room', ''))

        price_per_night = ROOM_PRICES.get(room_type, 199)
        total = price_per_night * nights
        reference = generate_reference()
        user_id = session.get('user_id')

        conn = get_db()
        conn.execute("""
            INSERT INTO bookings (user_id, room_type, checkin, checkout, guests, total_price, reference)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, room_type, checkin, checkout, guests, total, reference))
        conn.commit()
        conn.close()

        return render_template('confirmation.html',
            reference=reference, room_type=room_type,
            checkin=checkin, checkout=checkout,
            guests=guests, total=total, nights=nights)

    return render_template('booking.html', room=request.args.get('room', ''))

@app.route('/check_availability', methods=['POST'])
def check_avail():
    room_type = request.form.get('room_type')
    checkin = request.form.get('checkin')
    checkout = request.form.get('checkout')
    available = check_availability(room_type, checkin, checkout)
    return {'available': available}

@app.route('/reviews')
def reviews():
    conn = get_db()
    all_reviews = conn.execute("SELECT * FROM reviews ORDER BY created_at DESC").fetchall()
    conn.close()
    return render_template('reviews.html', reviews=all_reviews)

@app.route('/add_review', methods=['GET', 'POST'])
def add_review():
    if request.method == 'POST':
        fullname = request.form.get('fullname')
        rating = int(request.form.get('rating'))
        room_type = request.form.get('room_type')
        comment = request.form.get('comment')
        user_id = session.get('user_id')

        conn = get_db()
        conn.execute("INSERT INTO reviews (user_id, fullname, rating, room_type, comment) VALUES (?,?,?,?,?)",
                     (user_id, fullname, rating, room_type, comment))
        conn.commit()
        conn.close()
        flash("Thank you for your review!", "success")
        return redirect(url_for('reviews'))

    return render_template('add_review.html')

@app.route('/my_bookings')
def my_bookings():
    if not session.get('user_id'):
        return redirect(url_for('login'))
    conn = get_db()
    bookings = conn.execute("SELECT * FROM bookings WHERE user_id = ? ORDER BY created_at DESC", (session['user_id'],)).fetchall()
    conn.close()
    return render_template('my_bookings.html', bookings=bookings)

@app.route('/cancel_booking/<int:booking_id>', methods=['POST'])
def cancel_booking(booking_id):
    if not session.get('user_id'):
        return redirect(url_for('login'))
    conn = get_db()
    conn.execute("UPDATE bookings SET status = 'Cancelled' WHERE id = ? AND user_id = ?",
                 (booking_id, session['user_id']))
    conn.commit()
    conn.close()
    flash("Your booking has been cancelled.", "success")
    return redirect(url_for('my_bookings'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        conn.close()
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['user_name'] = user['fullname']
            flash(f"Welcome back, {user['fullname']}!", "success")
            return redirect(url_for('home'))
        else:
            flash("Invalid email or password.", "error")
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        fullname = request.form.get('fullname')
        email = request.form.get('email')
        password = request.form.get('password')
        hashed = generate_password_hash(password)
        try:
            conn = get_db()
            conn.execute("INSERT INTO users (fullname, email, password) VALUES (?, ?, ?)", (fullname, email, hashed))
            conn.commit()
            conn.close()
            flash("Account created! Please log in.", "success")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash("That email is already registered.", "error")
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
