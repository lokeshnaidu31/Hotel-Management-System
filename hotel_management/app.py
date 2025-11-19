from flask import Flask, render_template, request, redirect, session
import mysql.connector
from functools import wraps
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# MySQL Database Connection
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="loke@31",  
    database="hotel_db"
)
cursor = db.cursor()

# Authentication Decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect('/login')  # Redirect to login if not authenticated
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
@login_required
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        query = "SELECT * FROM users WHERE username = %s"
        cursor.execute(query, (username,))
        user = cursor.fetchone()
        if user and user[2] == password:
            session['user_id'] = user[0]
            session['role'] = user[3]
            return redirect('/')
        return "Invalid credentials, please try again."
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

@app.route('/cancel_bookings', methods=['GET', 'POST'])
@login_required
def cancel_bookings():
    if request.method == 'POST':
        user_id = request.form['user_id']
        # Fetch all bookings for the given user
        query = """
        SELECT b.booking_id, r.room_type, b.check_in_date, b.check_out_date, b.total_price, r.room_id
        FROM bookings b
        JOIN rooms r ON b.room_id = r.room_id
        WHERE b.customer_id = %s
        """
        cursor.execute(query, (user_id,))
        bookings = cursor.fetchall()
        return render_template('view_user_bookings.html', bookings=bookings, user_id=user_id)
    return render_template('cancel_bookings.html')

@app.route('/cancel_booking/<int:booking_id>/<int:room_id>', methods=['POST'])
@login_required
def cancel_booking(booking_id, room_id):
    try:
        # Delete the booking
        cursor.execute("DELETE FROM bookings WHERE booking_id = %s", (booking_id,))
        # Mark the room as available
        cursor.execute("UPDATE rooms SET is_available = TRUE WHERE room_id = %s", (room_id,))
        db.commit()
        return redirect('/cancel_bookings')
    except Exception as e:
        db.rollback()
        return f"Error occurred: {str(e)}"

@app.route('/add_customer', methods=['GET', 'POST'])
@login_required
def add_customer():
    if request.method == 'POST':
        name = request.form['name']
        phone = request.form['phone']
        email = request.form['email']
        address = request.form['address']
        query = "INSERT INTO customers (name, phone, email, address) VALUES (%s, %s, %s, %s)"
        cursor.execute(query, (name, phone, email, address))
        db.commit()
        return redirect('/')
    return render_template('add_customer.html')

@app.route('/view_customers')
@login_required
def view_customers():
    cursor.execute("SELECT * FROM customers")
    customers = cursor.fetchall()
    return render_template('view_customers.html', customers=customers)

@app.route('/book_room', methods=['GET', 'POST'])
@login_required
def book_room():
    if request.method == 'POST':
        customer_id = request.form['customer_id']
        room_id = request.form['room_ids']
        check_in_date = request.form['check_in_date']
        check_out_date = request.form['check_out_date']
        cursor.execute("SELECT price_per_night FROM rooms WHERE room_id = %s", (room_id,))
        price_per_night = cursor.fetchone()
        if not price_per_night:
            return "Room not found or unavailable."
        price_per_night = price_per_night[0]
        try:
            total_days = (datetime.strptime(check_out_date, '%Y-%m-%d') - datetime.strptime(check_in_date, '%Y-%m-%d')).days
        except ValueError:
            return "Invalid date format. Please enter the date in YYYY-MM-DD format."
        if total_days <= 0:
            return "Check-out date must be later than check-in date."
        total_price = price_per_night * total_days
        query = "INSERT INTO bookings (customer_id, room_id, check_in_date, check_out_date, total_price) VALUES (%s, %s, %s, %s, %s)"
        cursor.execute(query, (customer_id, room_id, check_in_date, check_out_date, total_price))
        cursor.execute("UPDATE rooms SET is_available = FALSE WHERE room_id = %s", (room_id,))
        db.commit()
        return redirect('/')
    cursor.execute("SELECT room_id, room_type, price_per_night FROM rooms WHERE is_available = TRUE")
    rooms = cursor.fetchall()
    return render_template('book_room.html', rooms=rooms)

@app.route('/view_bookings')
@login_required
def view_bookings():
    query = """
    SELECT b.booking_id, c.name, r.room_type, b.check_in_date, b.check_out_date, b.total_price
    FROM bookings b
    JOIN customers c ON b.customer_id = c.customer_id
    JOIN rooms r ON b.room_id = r.room_id
    """
    cursor.execute(query)
    bookings = cursor.fetchall()
    return render_template('view_bookings.html', bookings=bookings)

if __name__ == '__main__':
    app.run(debug=True)
