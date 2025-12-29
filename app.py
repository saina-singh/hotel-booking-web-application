from flask import Flask, render_template, request, redirect, url_for, session, make_response
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from flask import flash
from datetime import date

app = Flask(__name__, template_folder='templates', static_folder='static', static_url_path='/')
#secret key
app.secret_key='secret123'
#token generator
serializer=URLSafeTimedSerializer(app.secret_key)
import mysql.connector
db=mysql.connector.connect(
    host='localhost',
    user='root',
    password='sainasingh',
    database='worldhotels',
    port=3306
)

@app.after_request
def disable_cache(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

#MAIL CONFIG
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'singhsaina11@gmail.com'
app.config['MAIL_PASSWORD'] = 'zmrwibdkfscbsmts'
app.config['MAIL_DEFAULT_SENDER'] = 'singhsaina11@gmail.com'
mail=Mail(app)

@app.context_processor
def inject_endpoint():
    return dict(endpoint=request.endpoint)

#default route
@app.route('/')
def index():
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            h.hotel_id,
            h.hotel_name,
            c.name AS city
        FROM hotels h
        JOIN cities c ON c.city_id = h.city_id
        WHERE h.is_active = 1
        ORDER BY c.name
    """)

    hotels = cursor.fetchall()
    cursor.close()

    return render_template("index.html", hotels=hotels)

@app.route('/about')
def about():
    return render_template("about.html")

@app.route('/contact')
def contact():
    return render_template("contact.html")

@app.route('/gallery')
def gallery():
    return render_template('gallery.html')

@app.route('/deals')
def deals():
    return render_template("deals.html")

from flask import request  # make sure this is imported at top

@app.route('/hotels')
def hotels():
    searched_city = (request.args.get("city") or "").strip()

    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT h.hotel_id, c.name AS city, h.hotel_name
        FROM hotels h
        JOIN cities c ON c.city_id = h.city_id
        WHERE h.is_active = 1
        ORDER BY c.name
    """)
    hotels_list = cursor.fetchall()
    cursor.close()

    city_images = {
        "Aberdeen": "aberdeen.jpg",
        "Belfast": "belfast.jpg",
        "Birmingham": "birmingham.jpg",
        "Bristol": "bristol.jpg",
        "Cardiff": "cardiff.jpg",
        "Edinburgh": "edinburgh.jpg",
        "Glasgow": "glasgow.jpg",
        "London": "london.jpg",
        "Manchester": "manchester.jpg",
        "New Castle": "newcastle.jpg",
        "Norwich": "norwich.jpg",
        "Nottingham": "nottingham.jpg",
        "Oxford": "oxford.jpg",
        "Plymouth": "plymouth.jpg",
        "Swansea": "swansea.jpg",
        "Bournemouth": "bournemouth.jpg",
        "Kent": "kent.jpg",
    }

    for h in hotels_list:
        filename = city_images.get(h["city"], "default.jpg")
        h["img"] = f"images/hotels/{filename}"

    return render_template("hotels.html", hotels=hotels_list, searched_city=searched_city)




@app.route('/login', methods=['GET', 'POST'])
def login():
    msg = ''
    if request.method == 'POST':
        email = request.form['email']   
        password = request.form['password']

        cursor = db.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM users WHERE email=%s AND is_active=%s",
            (email, 1)
        )
        user = cursor.fetchone()

        if user and check_password_hash(user['password_hash'], password):
            session['loggedin'] = True
            session['user_id'] = user['user_id']
            session['email'] = user['email']
            session['role'] = user['role']   # 'ADMIN' or 'CUSTOMER'

            if user['role'] == 'ADMIN':
             redirect_url = url_for('admin_dashboard')
            else:
             redirect_url = url_for('user_dashboard')


            response = make_response(redirect(redirect_url))
            response.set_cookie('email', user['email'], max_age=60*60*24)
            return response
        else:
            msg = "Invalid email or password"

    return render_template("login.html", msg=msg)


@app.route('/admin/dashboard')
def admin_dashboard():
    if session.get('loggedin') and session.get('role') == 'ADMIN':
        cursor = db.cursor(dictionary=True)
        cursor.execute("""
            SELECT user_id, first_name, last_name, email, role, is_active
            FROM users
        """)
        users = cursor.fetchall()
        total_users = len(users)
        return render_template('admin/admin_dashboard.html',
                               users=users,
                               total_users=total_users)

    return redirect(url_for('login'))


@app.route('/user/dashboard')
def user_dashboard():
    if not (session.get('loggedin') and session.get('role') == 'CUSTOMER'):
        return redirect(url_for('login'))

    cursor = db.cursor(dictionary=True)

    # current user info
    cursor.execute("""
        SELECT user_id, first_name, last_name, email
        FROM users
        WHERE user_id = %s
    """, (session['user_id'],))
    me = cursor.fetchone()

    # bookings + converted total in selected currency (uses latest rate <= today)
    cursor.execute("""
        SELECT
          b.booking_id,
          b.booking_code,
          b.booking_status,
          b.created_at,
          b.check_in,
          b.check_out,
          b.currency_code,
          b.total_gbp,
          h.hotel_name,
          c.name AS city,

          xr.gbp_to_curr,
          ROUND(b.total_gbp * xr.gbp_to_curr, 2) AS total_in_currency

        FROM bookings b
        JOIN hotels h ON h.hotel_id = b.hotel_id
        JOIN cities c ON c.city_id = h.city_id

        LEFT JOIN exchange_rates xr
          ON xr.currency_code = b.currency_code
         AND xr.rate_date = (
            SELECT MAX(rate_date)
            FROM exchange_rates
            WHERE currency_code = b.currency_code
              AND rate_date <= CURRENT_DATE()
         )

        WHERE b.user_id = %s
        ORDER BY b.created_at DESC
    """, (session['user_id'],))
    bookings = cursor.fetchall()

    cursor.close()

    # If rate is missing, fall back to GBP display in template safely
    for b in bookings:
        if b.get("total_in_currency") is None:
            b["total_in_currency"] = b["total_gbp"]
            b["gbp_to_curr"] = 1.0

    return render_template('user/user_dashboard.html', me=me, bookings=bookings)

@app.route('/logout')
def logout():
    session.clear()
    response = make_response(redirect(url_for('login')))
    response.delete_cookie('email')
    return response

@app.route('/register', methods=['GET', 'POST'])
def register():
    msg = ''
    if request.method == 'POST':
        try:
            first_name = request.form.get('first_name', '').strip()
            last_name  = request.form.get('last_name', '').strip()
            email      = request.form.get('email', '').strip()
            password   = request.form.get('password', '')

            if not first_name or not last_name or not email or not password:
                return render_template("register.html", msg="Please fill in all fields.")

            cursor = db.cursor(dictionary=True)
            cursor.execute("SELECT user_id FROM users WHERE email=%s", (email,))
            if cursor.fetchone():
                cursor.close()
                return render_template("register.html", msg="Account already exists with this email.")
            hashed_password = generate_password_hash(password, method="pbkdf2:sha256")

            cursor.execute("""
                INSERT INTO users (first_name, last_name, email, password_hash, role, is_active)
                VALUES (%s, %s, %s, %s, 'CUSTOMER', 0)
            """, (first_name, last_name, email, hashed_password))
            db.commit()
            cursor.close()

            token = serializer.dumps(email, salt='email-confirm')
            link = url_for('activate', token=token, _external=True)

            try:
                email_msg = Message('Activate Your Account', recipients=[email])
                email_msg.body = f'Click the link to activate your account:\n{link}'
                mail.send(email_msg)
                msg = "Registration successful! Check your email to activate."
            except Exception as e:
                print("MAIL ERROR:", e)
                msg = f"Registered, but email failed. Activate manually: {link}"

            return render_template("register.html", msg=msg)

        except Exception as e:
            print("REGISTER ERROR:", e)
            return render_template("register.html", msg=f"Server error: {e}")

    return render_template("register.html", msg=msg)

@app.route('/activate/<token>')
def activate(token):
    try:
        email = serializer.loads(token, salt='email-confirm', max_age=3600)
    except:
        return "Activation link expired"

    cursor = db.cursor()
    cursor.execute("UPDATE users SET is_active=1 WHERE email=%s", (email,))
    db.commit()
    return "Account activated successfully!"


@app.route('/user')
def user():
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT first_name, last_name, email, role, is_active FROM users")
    users = cursor.fetchall()
    cursor.close()
    return render_template("user.html", users=users)

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if not session.get('loggedin'):
        return redirect(url_for('login'))

    user_id = session.get('user_id')
    msg = ""

    cursor = db.cursor(dictionary=True)

    # Update profile (optional)
    if request.method == 'POST':
        first_name = request.form.get('first_name', '').strip()
        last_name  = request.form.get('last_name', '').strip()
        phone      = request.form.get('phone', '').strip()

        if not first_name or not last_name:
            msg = "First name and last name are required."
        else:
            cursor.execute("""
                UPDATE users
                SET first_name=%s, last_name=%s, phone=%s
                WHERE user_id=%s
            """, (first_name, last_name, phone, user_id))
            db.commit()
            msg = "Profile updated successfully."

    # Fetch latest profile info
    cursor.execute("""
        SELECT user_id, first_name, last_name, email, phone, role, is_active, created_at
        FROM users
        WHERE user_id = %s
    """, (user_id,))
    me = cursor.fetchone()

    return render_template("profile.html", me=me, msg=msg)

from datetime import date

@app.route('/hotels/<int:hotel_id>')
def hotel_details(hotel_id):
    cursor = db.cursor(dictionary=True)

    # Hotel + city + rates + capacity
    cursor.execute("""
        SELECT h.hotel_id, h.hotel_name, h.address, c.name AS city,
               hcr.total_rooms, hcr.standard_peak_gbp, hcr.standard_offpeak_gbp
        FROM hotels h
        JOIN cities c ON c.city_id = h.city_id
        JOIN hotel_capacity_rates hcr ON hcr.hotel_id = h.hotel_id
        WHERE h.hotel_id = %s AND h.is_active = 1
    """, (hotel_id,))
    hotel = cursor.fetchone()
    if not hotel:
        cursor.close()
        return "Hotel not found", 404

    # Rooms + inventory + multipliers
    cursor.execute("""
        SELECT rt.room_type_id, rt.code, rt.max_guests,
               rt.base_multiplier, rt.second_guest_multiplier,
               inv.rooms_count
        FROM hotel_room_inventory inv
        JOIN room_types rt ON rt.room_type_id = inv.room_type_id
        WHERE inv.hotel_id = %s
        ORDER BY rt.room_type_id
    """, (hotel_id,))
    rooms = cursor.fetchall()

    # Features per room type
    cursor.execute("""
        SELECT rt.code AS room_code, GROUP_CONCAT(f.name ORDER BY f.name SEPARATOR ', ') AS features
        FROM room_type_features rtf
        JOIN room_types rt ON rt.room_type_id = rtf.room_type_id
        JOIN features f ON f.feature_id = rtf.feature_id
        WHERE rtf.hotel_id = %s
        GROUP BY rt.code
    """, (hotel_id,))
    features_rows = cursor.fetchall()
    cursor.close()

    features_map = {r["room_code"]: r["features"] for r in features_rows}

    # Attach features + images + simple nightly pricing preview
    room_images = {
        "STANDARD": "images/rooms/standard.jpg",
        "DOUBLE": "images/rooms/double.jpg",
        "FAMILY": "images/rooms/family.jpg",
        "SINGLE": "images/rooms/single.jpg",
        "DELUXE": "images/rooms/deluxe.jpg",
        "SUITE": "images/rooms/suite.jpg",
        "EXECUTIVE": "images/rooms/executive.jpg",
    }

    # show a default “today” price preview (offpeak/peak depends on month, keep simple)
    # (you can improve later with real check-in date)
    month = date.today().month
    is_peak = (4 <= month <= 8) or (month in (11, 12))
    standard_rate = float(hotel["standard_peak_gbp"] if is_peak else hotel["standard_offpeak_gbp"])

    for r in rooms:
        r["features"] = features_map.get(r["code"], "—")
        r["img"] = room_images.get(r["code"], "images/rooms/default.jpg")
        r["nightly_from_gbp"] = round(standard_rate * float(r["base_multiplier"]), 2)

    # hotel image (city-based)
    hotel["img"] = f"images/hotels/{hotel['city'].lower().replace(' ', '')}.jpg"

    return render_template("hotel_details.html", hotel=hotel, rooms=rooms)

@app.route('/hotels/<int:hotel_id>/rooms/<room_code>')
def room_details(hotel_id, room_code):
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT h.hotel_id, h.hotel_name, c.name AS city
        FROM hotels h
        JOIN cities c ON c.city_id = h.city_id
        WHERE h.hotel_id = %s
    """, (hotel_id,))
    hotel = cursor.fetchone()
    if not hotel:
        cursor.close()
        return "Hotel not found", 404

    cursor.execute("""
        SELECT rt.room_type_id, rt.code, rt.max_guests,
               rt.base_multiplier, rt.second_guest_multiplier,
               inv.rooms_count
        FROM room_types rt
        JOIN hotel_room_inventory inv
          ON inv.room_type_id = rt.room_type_id AND inv.hotel_id = %s
        WHERE rt.code = %s
        LIMIT 1
    """, (hotel_id, room_code))
    room = cursor.fetchone()
    if not room:
        cursor.close()
        return "Room type not found", 404

    cursor.execute("""
        SELECT f.name
        FROM room_type_features rtf
        JOIN features f ON f.feature_id = rtf.feature_id
        JOIN room_types rt ON rt.room_type_id = rtf.room_type_id
        WHERE rtf.hotel_id = %s AND rt.code = %s
        ORDER BY f.name
    """, (hotel_id, room_code))
    features = [row["name"] for row in cursor.fetchall()]
    cursor.close()

    room_images = {
        "STANDARD": "images/rooms/standard.jpg",
        "DOUBLE": "images/rooms/double.jpg",
        "FAMILY": "images/rooms/family.jpg",
        "SINGLE": "images/rooms/single.jpg",
        "DELUXE": "images/rooms/deluxe.jpg",
        "SUITE": "images/rooms/suite.jpg",
        "EXECUTIVE": "images/rooms/executive.jpg",
    }
    room["img"] = room_images.get(room["code"], "images/rooms/default.jpg")
    room["features_list"] = features

    return render_template("room_details.html", hotel=hotel, room=room)


@app.route('/book/<int:hotel_id>', methods=['POST'])
def book(hotel_id):
    if not session.get('loggedin'):
        return redirect(url_for('login'))

    try:
        room_type_id  = int(request.form.get('room_type_id'))
        check_in_str  = request.form.get('check_in')
        check_out_str = request.form.get('check_out')
        rooms_qty     = int(request.form.get('rooms_qty', 1))
        guests        = int(request.form.get('guests', 1))
        currency_code = request.form.get('currency_code', 'GBP')

        if not check_in_str or not check_out_str:
            return "Missing dates", 400

        check_in  = datetime.strptime(check_in_str, "%Y-%m-%d").date()
        check_out = datetime.strptime(check_out_str, "%Y-%m-%d").date()

        today = date.today()
        if check_in < today:
            return "Check-in cannot be in the past.", 400
        if check_out <= check_in:
            return "Check-out must be after check-in.", 400

        nights = (check_out - check_in).days
        if nights > 30:
            return "Stay cannot be more than 30 nights.", 400

        max_checkin = today + relativedelta(months=3)
        if check_in > max_checkin:
            return "Bookings can only be made up to 3 months in advance.", 400

        cursor = db.cursor()

        # 1) create booking
        args = [
            int(session['user_id']),
            int(hotel_id),
            check_in,
            check_out,
            currency_code,
            0,      # OUT booking_id
            ""      # OUT booking_code
        ]
        result = cursor.callproc("sp_create_booking", args)

        # ✅ IMPORTANT: clear stored results
        for r in cursor.stored_results():
            r.fetchall()

        booking_id = result[5]
        booking_code = result[6]

        # 2) add booking room line
        cursor.callproc("sp_add_booking_room", [
            int(booking_id),
            int(room_type_id),
            int(rooms_qty),
            int(guests)
        ])

        # ✅ IMPORTANT: clear stored results again
        for r in cursor.stored_results():
            r.fetchall()

        # 3) confirm booking so it won't stay PENDING
        cursor.execute(
            "UPDATE bookings SET booking_status='CONFIRMED' WHERE booking_id=%s",
            (booking_id,)
        )

        # optional simulated payment
        cursor.execute(
            "UPDATE payments SET payment_status='PAID', paid_at=NOW() WHERE booking_id=%s",
            (booking_id,)
        )

        db.commit()
        cursor.close()

        return render_template("booking_confirm.html",
                               booking_id=booking_id,
                               booking_code=booking_code)

    except Exception as e:
        import traceback
        print("BOOKING ERROR:", e)
        traceback.print_exc()
        return f"Booking failed: {e}", 500

@app.route('/cancel-booking/<int:booking_id>', methods=['POST'])
def cancel_booking(booking_id):
    if not session.get('loggedin'):
        return redirect(url_for('login'))

    try:
        reason = request.form.get('reason', '').strip()

        cursor = db.cursor()

        # IMPORTANT: call your stored procedure
        cursor.callproc("sp_cancel_booking", [
            booking_id,
            reason
        ])

        db.commit()
        cursor.close()

        return redirect(url_for('user_dashboard'))

    except Exception as e:
        import traceback
        print("CANCEL ERROR:", e)
        traceback.print_exc()
        return f"Cancellation failed: {e}", 500

    
if __name__== '__main__':
    app.run(host="127.0.0.1", port=5000, debug=True)