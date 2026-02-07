from flask import Flask, render_template, request, redirect, url_for, session, make_response
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date, datetime, timedelta
import mysql.connector
from dateutil.relativedelta import relativedelta
from flask import flash, jsonify, send_file, abort
from datetime import date
from io import BytesIO
from typing import Optional
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import os
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, template_folder='templates', static_folder='static', static_url_path='/')
UPLOAD_FOLDER = os.path.join(app.root_path, "static", "uploads", "profiles")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024  # 2MB limit
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

BASE_URL = 'https://24071247.tbcstudentserver.com/'

#secret key
app.secret_key='secret123'
#token generator
serializer=URLSafeTimedSerializer(app.secret_key)

db_config = {
    "host": os.getenv("DB_HOST"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME"),
    "port": int(os.getenv("DB_PORT", 3306))
}

def get_db():
    return mysql.connector.connect(**db_config)

def get_cookie_prefs(user_id):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT necessary, analytics, marketing
        FROM cookie_preferences
        WHERE user_id=%s
        LIMIT 1
    """, (user_id,))
    prefs = cursor.fetchone()
    cursor.close()
    db.close()

    # default if no record yet
    if not prefs:
        return {"necessary": 1, "analytics": 0, "marketing": 0}

    # ensure ints
    return {
        "necessary": int(prefs.get("necessary", 1)),
        "analytics": int(prefs.get("analytics", 0)),
        "marketing": int(prefs.get("marketing", 0))
    }

def save_cookie_prefs(user_id, analytics, marketing):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        INSERT INTO cookie_preferences (user_id, necessary, analytics, marketing)
        VALUES (%s, 1, %s, %s)
        ON DUPLICATE KEY UPDATE
          necessary=1,
          analytics=VALUES(analytics),
          marketing=VALUES(marketing)
    """, (user_id, int(analytics), int(marketing)))
    db.commit()
    cursor.close()
    db.close()

@app.route("/cookies", methods=["GET", "POST"])
def cookies_settings():
    if not session.get("loggedin"):
        return redirect(url_for("login"))

    user_id = session["user_id"]

    if request.method == "POST":
        # necessary is always ON, cannot be disabled
        analytics = 1 if request.form.get("analytics") == "1" else 0
        marketing = 1 if request.form.get("marketing") == "1" else 0

        save_cookie_prefs(user_id, analytics, marketing)
        flash("Cookie settings saved.", "success")
        return redirect(url_for("cookies_settings"))

    prefs = get_cookie_prefs(user_id)
    return render_template("cookies_settings.html", prefs=prefs)

@app.route("/cookies/quick", methods=["POST"])
def cookies_quick():
    if not session.get("loggedin"):
        return jsonify({"ok": False}), 401

    data = request.get_json(silent=True) or {}
    action = (data.get("action") or "").lower()

    if action == "accept_all":
        save_cookie_prefs(session["user_id"], 1, 1)
    elif action == "reject_optional":
        save_cookie_prefs(session["user_id"], 0, 0)
    else:
        return jsonify({"ok": False, "error": "invalid_action"}), 400

    return jsonify({"ok": True})

def has_cookie_record(user_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT 1 FROM cookie_preferences WHERE user_id=%s LIMIT 1", (user_id,))
    row = cursor.fetchone()
    cursor.close()
    db.close()
    return bool(row)

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
    show_cookie_banner = False
    if session.get("loggedin"):
        show_cookie_banner = not has_cookie_record(session["user_id"])
    return dict(endpoint=request.endpoint, show_cookie_banner=show_cookie_banner)

#default route
@app.route('/')
def index():
    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT * FROM hotels")
    hotels = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template("index.html", hotels=hotels)


@app.route('/about')
def about():
    return render_template("about.html")

@app.route('/contact')
def contact():
    return render_template("contact.html")

@app.route('/privacy')
def privacy():
    return render_template("privacy.html")

@app.route('/gallery')
def gallery():
    return render_template('gallery.html')

@app.route('/deals')
def deals():
    return render_template("deals.html")

@app.route('/hotels')
def hotels():
    searched_city = (request.args.get("city") or "").strip()
    room = (request.args.get("room") or "").strip().upper()
    checkin = (request.args.get("checkin") or "").strip()  
    db = get_db()
    cursor = db.cursor(dictionary=True)

    sql = """
        SELECT DISTINCT h.hotel_id, c.name AS city, h.hotel_name
        FROM hotels h
        JOIN cities c ON c.city_id = h.city_id
        WHERE h.is_active = 1
    """
    params = []

    if searched_city:
        sql += " AND c.name LIKE %s"
        params.append(f"%{searched_city}%")

    if room:
        sql += """
            AND EXISTS (
                SELECT 1
                FROM hotel_room_inventory inv
                JOIN room_types rt ON rt.room_type_id = inv.room_type_id
                WHERE inv.hotel_id = h.hotel_id
                  AND rt.code = %s
            )
        """
        params.append(room)

    sql += " ORDER BY c.name"

    cursor.execute(sql, tuple(params))
    hotels_list = cursor.fetchall()
    cursor.close()
    db.close()

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

    return render_template(
        "hotels.html",
        hotels=hotels_list,
        searched_city=searched_city,
        searched_room=room,
        checkin=checkin  
    )

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        db = get_db()
        cursor = db.cursor(dictionary=True)

        cursor.execute(
        "SELECT * FROM users WHERE email=%s AND is_active=%s",
        (email, 1)
        )
        user = cursor.fetchone()

        cursor.close()
        db.close()


        if user and check_password_hash(user['password_hash'], password):
            session['loggedin'] = True
            session['user_id'] = user['user_id']
            session['email'] = user['email']
            session['role'] = user['role']
            if not has_cookie_record(session["user_id"]):
                pass
            session['profile_image'] = user.get('profile_image')

            flash("Logged in successfully!", "success")

            next_url = request.args.get("next")
            if next_url:
                return redirect(next_url)

            return redirect(url_for('admin_dashboard' if user['role']=='ADMIN' else 'user_dashboard'))

        flash("Invalid email or password.", "danger")

    return render_template("login.html")


@app.route('/admin/dashboard')
def admin_dashboard():
    if session.get('loggedin') and session.get('role') == 'ADMIN':
        db = get_db()
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
    cursor.close()
    db.close()
    return redirect(url_for('login'))


@app.route('/user/dashboard')
def user_dashboard():
    if not (session.get('loggedin') and session.get('role') == 'CUSTOMER'):
        return redirect(url_for('login'))

    tab = (request.args.get("tab") or "all").lower().strip()  
    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT user_id, first_name, last_name, email
        FROM users
        WHERE user_id = %s
        LIMIT 1
    """, (session['user_id'],))
    me = cursor.fetchone()

    if not me:
        cursor.close()
        db.close()
        session.clear()
        return redirect(url_for("login"))

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
    all_bookings = cursor.fetchall() or []

    cursor.close()
    db.close()

    for b in all_bookings:
        if b.get("total_in_currency") is None:
            b["total_in_currency"] = b.get("total_gbp", 0)
            b["gbp_to_curr"] = 1.0

    if tab == "cancelled":
        bookings = [b for b in all_bookings if b.get("booking_status") == "CANCELLED"]
    elif tab == "active":
        bookings = [b for b in all_bookings if b.get("booking_status") != "CANCELLED"]
    else:
        bookings = all_bookings

    return render_template(
        'user/user_dashboard.html',
        me=me,
        bookings=bookings,              
        all_bookings=all_bookings,     
        tab=tab
    )

@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    response = make_response(redirect(url_for('login')))
    response.delete_cookie('email')
    return response

@app.route('/register', methods=['GET', 'POST'])
def register():
    msg = ''
    if request.method == 'POST':
        db = get_db()
        cursor = db.cursor(dictionary=True)
        try:
            first_name = request.form.get('first_name', '').strip()
            last_name  = request.form.get('last_name', '').strip()
            email      = request.form.get('email', '').strip()
            password   = request.form.get('password', '')

            if not first_name or not last_name or not email or not password:
                flash("Please fill in all fields.", "danger")
                return render_template("register.html", msg="Please fill in all fields.")

            cursor.execute("SELECT user_id FROM users WHERE email=%s", (email,))
            if cursor.fetchone():
                flash("An account already exists with this email.", "warning")
                return render_template("register.html", msg="Account already exists with this email.")

            hashed_password = generate_password_hash(password, method="pbkdf2:sha256")
            cursor.execute("""
                INSERT INTO users (first_name, last_name, email, password_hash, role, is_active)
                VALUES (%s, %s, %s, %s, 'CUSTOMER', 0)
            """, (first_name, last_name, email, hashed_password))
            db.commit()

            token = serializer.dumps(email, salt='email-confirm')
            link = url_for('activate', token=token, _external=True)

            try:
                email_msg = Message('Activate Your Account', recipients=[email])
                email_msg.body = f'Click the link to activate your account:\n{link}'
                mail.send(email_msg)
                flash("Registration successful! Please check your email to activate your account.", "success")
            except Exception as e:
                print("MAIL ERROR:", e)
                flash("Registered, but email failed. Please contact support.", "warning")

            return redirect(url_for('login'))

        except Exception as e:
            import traceback
            traceback.print_exc()  # <-- IMPORTANT so you see the real cause
            flash(f"Register failed: {e}", "danger")
            return render_template("register.html", msg="Server error")

        finally:
            cursor.close()

    return render_template("register.html", msg=msg)

@app.route('/activate/<token>')
def activate(token):
    try:
        email = serializer.loads(token, salt='email-confirm', max_age=3600)
    except:
        flash("Activation link expired. Please register again.", "danger")
        return redirect(url_for('register'))
    db = get_db()
    cursor = db.cursor()
    cursor.execute("UPDATE users SET is_active=1 WHERE email=%s", (email,))
    db.commit()
    cursor.close()
    db.close()

    flash("Account activated successfully! You can now log in.", "success")
    return redirect(url_for('login'))

@app.route('/user')
def user():
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT first_name, last_name, email, role, is_active FROM users")
    users = cursor.fetchall()
    cursor.close()
    db.close()
    return render_template("user.html", users=users)

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if not session.get('loggedin'):
        return redirect(url_for('login'))

    user_id = session.get('user_id')
    msg = ""
    db = get_db()
    cursor = db.cursor(dictionary=True)

    if request.method == 'POST':
        first_name = request.form.get('first_name', '').strip()
        last_name  = request.form.get('last_name', '').strip()
        phone      = request.form.get('phone', '').strip()

        if not first_name or not last_name:
            msg = "First name and last name are required."
        else:
            file = request.files.get("profile_image")
            new_filename = None

            if file and file.filename:
                if not allowed_file(file.filename):
                    msg = "Invalid file type. Use PNG, JPG, JPEG, or WEBP."
                else:
                    ext = file.filename.rsplit(".", 1)[1].lower()
                    new_filename = f"user_{user_id}.{ext}"
                    save_path = os.path.join(app.config["UPLOAD_FOLDER"], new_filename)
                    file.save(save_path)

            if new_filename:
                cursor.execute("""
                    UPDATE users
                    SET first_name=%s, last_name=%s, phone=%s, profile_image=%s
                    WHERE user_id=%s
                """, (first_name, last_name, phone, new_filename, user_id))
            else:
                cursor.execute("""
                    UPDATE users
                    SET first_name=%s, last_name=%s, phone=%s
                    WHERE user_id=%s
                """, (first_name, last_name, phone, user_id))

            db.commit()
            session['profile_image'] = new_filename
            if msg == "":
                msg = "Profile updated successfully."

    # Fetch latest profile info
    cursor.execute("""
        SELECT user_id, first_name, last_name, email, phone, role, is_active, created_at, profile_image
        FROM users
        WHERE user_id = %s
    """, (user_id,))
    me = cursor.fetchone()
    cursor.close()
    db.close()

    return render_template("profile.html", me=me, msg=msg)

@app.route('/hotels/<int:hotel_id>')
def hotel_details(hotel_id):
    checkin_str = (request.args.get("checkin") or "").strip()  
    season_override = (request.args.get("season") or "").strip().lower()
    checkin_date = parse_checkin_arg(checkin_str)            
    if not checkin_date:
        checkin_date = date.today()  
    db = get_db()
    cursor = db.cursor(dictionary=True)

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
        db.close()
        return "Hotel not found", 404

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
    db.close()

    features_map = {r["room_code"]: r["features"] for r in features_rows}

    room_images = {
        "STANDARD": "images/rooms/standard.jpg",
        "DOUBLE": "images/rooms/double.jpg",
        "FAMILY": "images/rooms/family.jpg",
        "SINGLE": "images/rooms/single.jpg",
        "DELUXE": "images/rooms/deluxe.jpg",
        "SUITE": "images/rooms/suite.jpg",
        "EXECUTIVE": "images/rooms/executive.jpg",
    }

    peak = resolve_season(checkin_str, season_override)
    standard_rate = float(hotel["standard_peak_gbp"] if peak else hotel["standard_offpeak_gbp"])

    for r in rooms:
        r["features"] = features_map.get(r["code"], "—")
        r["img"] = room_images.get(r["code"], "images/rooms/default.jpg")
        r["nightly_from_gbp"] = round(standard_rate * float(r["base_multiplier"]), 2)

    hotel["img"] = f"images/hotels/{hotel['city'].lower().replace(' ', '')}.jpg"

    return render_template(
        "hotel_details.html",
        hotel=hotel,
        rooms=rooms,
        checkin=checkin_str,          
        season=("Peak" if peak else "Off-Peak"),  
    )

@app.route('/hotels/<int:hotel_id>/rooms/<room_code>')
def room_details(hotel_id, room_code):
    checkin_str = (request.args.get("checkin") or "").strip()
    season_override = (request.args.get("season") or "").strip().lower()
    checkin_date = parse_checkin_arg(checkin_str)            
    if not checkin_date:
        checkin_date = date.today()
    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT h.hotel_id, h.hotel_name, h.address, c.name AS city,
               COALESCE(hcr.standard_peak_gbp, 0) AS standard_peak_gbp,
               COALESCE(hcr.standard_offpeak_gbp, 0) AS standard_offpeak_gbp
        FROM hotels h
        JOIN cities c ON c.city_id = h.city_id
        LEFT JOIN hotel_capacity_rates hcr ON hcr.hotel_id = h.hotel_id
        WHERE h.hotel_id = %s
        LIMIT 1
    """, (hotel_id,))
    hotel = cursor.fetchone()
    if not hotel:
        cursor.close()
        db.close()
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
        db.close()
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
    db.close()

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

    peak = resolve_season(checkin_str, season_override)
    standard_rate = float(hotel["standard_peak_gbp"] if peak else hotel["standard_offpeak_gbp"])  # NEW
    room["nightly_from_gbp"] = round(standard_rate * float(room["base_multiplier"]), 2)

    room_copy = {
        "SINGLE": {
            "title": "Perfect for solo travellers",
            "desc": "A compact, comfortable space ideal for short business trips or quick city stays.",
            "why": ["Best value for solo trips", "Easy check-in, easy stay", "Comfort-focused layout"],
        },
        "STANDARD": {
            "title": "A balanced, comfortable stay",
            "desc": "Our most popular option with all the essentials for a relaxed city break.",
            "why": ["Great value", "Comfortable for 1–2 guests", "Most requested room type"],
        },
        "DOUBLE": {
            "title": "Ideal for couples",
            "desc": "A cosy layout with extra space and comfort — great for two guests.",
            "why": ["Better space than Standard", "Great for couples", "Relaxed city stay"],
        },
        "FAMILY": {
            "title": "Made for families",
            "desc": "More room, more comfort — suitable for parents and children with practical space.",
            "why": ["More space", "Family friendly", "Comfort for longer stays"],
        },
        "DELUXE": {
            "title": "Upgrade your comfort",
            "desc": "Premium feel with added comfort — perfect when you want something special.",
            "why": ["More premium feel", "Better comfort", "Great for special trips"],
        },
        "SUITE": {
            "title": "Luxury suite experience",
            "desc": "The best choice for extra space, premium comfort, and a memorable stay.",
            "why": ["Most spacious", "Premium comfort", "Top-tier experience"],
        },
        "EXECUTIVE": {
            "title": "Business-class convenience",
            "desc": "Designed for business travellers needing comfort and efficiency.",
            "why": ["Great for business trips", "Comfort + space", "Premium feel"],
        },
    }

    info = room_copy.get(room["code"], {
        "title": "Comfortable stay",
        "desc": "A well-designed room with the essentials for a clean and relaxing stay.",
        "why": ["Comfortable", "Good value", "Easy stay"],
    })

    room["title"] = info["title"]
    room["desc"] = info["desc"]
    room["why_list"] = info["why"]
    room["features_list"] = features

    return render_template(
        "room_details.html",
        hotel=hotel,
        room=room,
        checkin=checkin_str,                
        season=("Peak" if peak else "Off-Peak"),
        season_override=season_override
    )

@app.route('/book/<int:hotel_id>', methods=['POST'])
def book(hotel_id):
    if not session.get('loggedin'):
        flash("Please log in or create an account to book a room.", "warning")
        return redirect(url_for('login', next=request.referrer or url_for('hotels')))

    try:
        room_type_id  = int(request.form.get('room_type_id'))
        check_in_str  = request.form.get('check_in')
        check_out_str = request.form.get('check_out')
        rooms_qty     = int(request.form.get('rooms_qty', 1))
        guests        = int(request.form.get('guests', 1))
        currency_code = request.form.get('currency_code', 'GBP')

        payment_method = (request.form.get('payment_method') or 'CARD').upper().strip()
        allowed_methods = {'CARD', 'PAYPAL', 'BANK', 'CASH'}
        if payment_method not in allowed_methods:
            return "Invalid payment method", 400

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
            return "Stay cannot exceed 30 nights.", 400

        if (check_in - today).days > 90:
            return "Bookings allowed only up to 90 days in advance.", 400
        db = get_db()
        cursor = db.cursor()

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

        for r in cursor.stored_results():
            r.fetchall()

        booking_id = result[5]

        cursor.callproc("sp_add_booking_room", [
            int(booking_id),
            int(room_type_id),
            int(rooms_qty),
            int(guests)
        ])

        for r in cursor.stored_results():
            r.fetchall()

        cursor.execute(
            "UPDATE bookings SET booking_status='CONFIRMED' WHERE booking_id=%s",
            (booking_id,)
        )

        cursor.execute(
            """
            UPDATE payments
            SET payment_status='PAID',
                paid_at=NOW(),
                provider=%s
            WHERE booking_id=%s
            """,
            (payment_method, booking_id)
        )

        db.commit()
        cursor.close()
        db.close()

        # success notification
        payment_labels = {
            "CARD": "Card payment completed successfully.",
            "PAYPAL": "PayPal payment completed successfully.",
            "BANK": "Bank transfer completed successfully.",
            "CASH": "Pay at hotel selected. Booking confirmed."
        }
        flash(payment_labels.get(payment_method, "Payment completed successfully."), "success")

        return redirect(url_for("receipt_download", booking_id=booking_id))

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
        reason = (request.form.get('reason') or "").strip()
        delete_after = request.form.get('delete_after') == "1"
        db = get_db()
        cursor = db.cursor(dictionary=True)

        # make sure this booking belongs to the logged-in user
        cursor.execute("SELECT user_id FROM bookings WHERE booking_id=%s", (booking_id,))
        row = cursor.fetchone()
        if not row or row["user_id"] != session["user_id"]:
            cursor.close()
            db.close()
            return "Not allowed", 403

        # 1) cancel using stored procedure
        cursor2 = db.cursor()
        cursor2.callproc("sp_cancel_booking", [booking_id, reason])

        # clear any stored results
        for r in cursor2.stored_results():
            r.fetchall()

        # 2) optionally delete after cancel
        if delete_after:
            cursor.execute("DELETE FROM bookings WHERE booking_id=%s AND user_id=%s", (booking_id, session["user_id"]))

        db.commit()
        cursor2.close()
        db.close()
        cursor.close()
        db.close()

        return redirect(url_for('user_dashboard'))

    except Exception as e:
        import traceback
        print("CANCEL ERROR:", e)
        traceback.print_exc()
        return f"Cancellation failed: {e}", 500

@app.route('/delete-booking/<int:booking_id>', methods=['POST'])
def delete_booking(booking_id):
    if not session.get('loggedin'):
        return redirect(url_for('login'))

    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)

        # only allow deleting your own booking
        cursor.execute("""
            SELECT user_id, booking_status
            FROM bookings
            WHERE booking_id=%s
        """, (booking_id,))
        b = cursor.fetchone()

        if not b or b["user_id"] != session["user_id"]:
            cursor.close()
            db.close()
            return "Not allowed", 403

        # (recommended) only delete if already cancelled
        if b["booking_status"] != "CANCELLED":
            cursor.close()
            db.close()
            return "You can only delete cancelled bookings.", 400

        cursor.execute("DELETE FROM bookings WHERE booking_id=%s AND user_id=%s", (booking_id, session["user_id"]))
        db.commit()
        cursor.close()
        db.close()

        return redirect(url_for('user_dashboard'))

    except Exception as e:
        import traceback
        print("DELETE ERROR:", e)
        traceback.print_exc()
        return f"Delete failed: {e}", 500

@app.route('/payment/<int:booking_id>', methods=['GET', 'POST'])
def payment(booking_id):
    if not session.get('loggedin'):
        return redirect(url_for('login'))

    msg = ""
    db = get_db()
    cursor = db.cursor(dictionary=True)

    # make sure booking belongs to user
    cursor.execute("""
        SELECT b.booking_id, b.booking_code, b.user_id, b.hotel_id,
               b.check_in, b.check_out, b.total_gbp, b.booking_status,
               h.hotel_name, c.name AS city
        FROM bookings b
        JOIN hotels h ON h.hotel_id = b.hotel_id
        JOIN cities c ON c.city_id = h.city_id
        WHERE b.booking_id=%s
        LIMIT 1
    """, (booking_id,))
    summary = cursor.fetchone()

    if not summary or summary["user_id"] != session["user_id"]:
        cursor.close()
        db.close()
        return "Not allowed", 403

    # if already paid/confirmed
    if summary["booking_status"] == "CONFIRMED":
        cursor.close()
        db.close()
        return redirect(url_for("user_dashboard"))

    if request.method == "POST":
        payment_method = (request.form.get("payment_method") or "").upper().strip()
        allowed = {"CARD", "PAYPAL", "BANK", "CASH"}

        if payment_method not in allowed:
            msg = "Please select a valid payment method."
        else:
            # mark payment as PAID + store method in provider
            cursor.execute("""
                UPDATE payments
                SET payment_status='PAID',
                    paid_at=NOW(),
                    provider=%s
                WHERE booking_id=%s
            """, (payment_method, booking_id))

            # confirm booking
            cursor.execute("""
                UPDATE bookings
                SET booking_status='CONFIRMED'
                WHERE booking_id=%s
            """, (booking_id,))

            db.commit()
            cursor.close()
            db.close()

            return redirect(url_for("user_dashboard"))

    cursor.close()
    db.close()
    return render_template("payment.html", summary=summary, msg=msg)

@app.route("/admin/search")
def admin_search():
    # admin-only
    if not (session.get("loggedin") and session.get("role") == "ADMIN"):
        return jsonify({"error": "unauthorized"}), 403

    q = (request.args.get("q") or "").strip()
    if not q:
        return jsonify({"cities": [], "rooms": [], "users": []})

    like = f"%{q}%"
    db = get_db()
    cursor = db.cursor(dictionary=True)

    # Cities
    cursor.execute("""
        SELECT city_id, name
        FROM cities
        WHERE name LIKE %s
        ORDER BY name
        LIMIT 8
    """, (like,))
    cities = cursor.fetchall()

    # Rooms (room types)
    cursor.execute("""
        SELECT room_type_id, code, max_guests
        FROM room_types
        WHERE code LIKE %s
        ORDER BY code
        LIMIT 8
    """, (like.upper(),))
    rooms = cursor.fetchall()

    # Users
    cursor.execute("""
        SELECT user_id, first_name, last_name, email, role
        FROM users
        WHERE first_name LIKE %s
           OR last_name LIKE %s
           OR email LIKE %s
        ORDER BY user_id DESC
        LIMIT 8
    """, (like, like, like))
    users = cursor.fetchall()

    cursor.close()
    db.close()
    return jsonify({"cities": cities, "rooms": rooms, "users": users})

@app.route("/receipt/<int:booking_id>")
def receipt(booking_id):
    if not session.get("loggedin"):
        return redirect(url_for("login"))
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT
          b.booking_id, b.booking_code, b.booking_status, b.created_at,
          b.check_in, b.check_out, b.total_gbp,
          u.first_name, u.last_name, u.email,
          h.hotel_name, c.name AS city,
          COALESCE(p.provider, '') AS provider
        FROM bookings b
        JOIN users u ON u.user_id = b.user_id
        JOIN hotels h ON h.hotel_id = b.hotel_id
        JOIN cities c ON c.city_id = h.city_id
        LEFT JOIN payments p ON p.booking_id = b.booking_id
        WHERE b.booking_id = %s
        LIMIT 1
    """, (booking_id,))
    r = cursor.fetchone()
    cursor.close()
    db.close()

    if not r:
        return "Receipt not found", 404

    # security: user can only view their own receipt unless admin
    if session.get("role") != "ADMIN" and r["email"] != session.get("email"):
        return "Not allowed", 403

    return render_template("receipt.html", r=r)

@app.route("/receipt/<int:booking_id>/pdf")
def receipt_pdf(booking_id):
    if not session.get("loggedin"):
        return redirect(url_for("login"))
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT
          b.booking_id, b.booking_code, b.booking_status, b.created_at,
          b.check_in, b.check_out, b.total_gbp,
          u.first_name, u.last_name, u.email,
          h.hotel_name, c.name AS city,
          COALESCE(p.provider, '') AS provider
        FROM bookings b
        JOIN users u ON u.user_id = b.user_id
        JOIN hotels h ON h.hotel_id = b.hotel_id
        JOIN cities c ON c.city_id = h.city_id
        LEFT JOIN payments p ON p.booking_id = b.booking_id
        WHERE b.booking_id = %s
        LIMIT 1
    """, (booking_id,))
    r = cursor.fetchone()
    cursor.close()
    db.close()

    if not r:
        return "Receipt not found", 404

    if session.get("role") != "ADMIN" and r["email"] != session.get("email"):
        return "Not allowed", 403

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4

    y = height - 60
    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, y, "World Hotels — Booking Receipt")

    y -= 30
    c.setFont("Helvetica", 11)
    c.drawString(50, y, f"Booking Code: {r['booking_code']}")
    y -= 18
    c.drawString(50, y, f"Status: {r['booking_status']}")
    y -= 18
    c.drawString(50, y, f"Created: {r['created_at']}")

    y -= 24
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Guest")
    y -= 16
    c.setFont("Helvetica", 11)
    c.drawString(50, y, f"{r['first_name']} {r['last_name']}  •  {r['email']}")

    y -= 24
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Hotel")
    y -= 16
    c.setFont("Helvetica", 11)
    c.drawString(50, y, f"{r['hotel_name']}  •  {r['city']}")

    y -= 24
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Stay & Payment")
    y -= 16
    c.setFont("Helvetica", 11)
    c.drawString(50, y, f"Check-in: {r['check_in']}   Check-out: {r['check_out']}")
    y -= 16
    c.drawString(50, y, f"Payment Method: {r['provider']}")

    y -= 28
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, f"Total (GBP):  £{r['total_gbp']}")

    y -= 40
    c.setFont("Helvetica", 10)
    c.drawString(50, y, "Thank you for booking with World Hotels!")

    c.showPage()
    c.save()

    buf.seek(0)
    filename = f"receipt_{r['booking_code']}.pdf"
    return send_file(buf, as_attachment=True, download_name=filename, mimetype="application/pdf")

@app.route("/receipt/<int:booking_id>/download")
def receipt_download(booking_id):
    if not session.get("loggedin"):
        return redirect(url_for("login"))
    return render_template("receipt_download.html", booking_id=booking_id)

def admin_only():
    return session.get("loggedin") and session.get("role") == "ADMIN"

@app.route("/admin/users")
def admin_users():
    if not (session.get("loggedin") and session.get("role") == "ADMIN"):
        return redirect(url_for("login"))

    q = (request.args.get("q") or "").strip()
    like = f"%{q}%"
    db = get_db()
    cursor = db.cursor(dictionary=True)

    if q:
        cursor.execute("""
            SELECT user_id, first_name, last_name, email, role, is_active
            FROM users
            WHERE first_name LIKE %s OR last_name LIKE %s OR email LIKE %s
            ORDER BY user_id DESC
            LIMIT 200
        """, (like, like, like))
    else:
        cursor.execute("""
            SELECT user_id, first_name, last_name, email, role, is_active
            FROM users
            ORDER BY user_id DESC
            LIMIT 200
        """)
    users = cursor.fetchall()

    cursor.execute("SELECT COUNT(*) AS n FROM users")
    total_users = cursor.fetchone()["n"]

    cursor.close()
    db.close()

    return render_template("admin/admin_users.html", users=users, total_users=total_users)

@app.route("/admin/users/add", methods=["POST"])
def admin_users_add():
    if not (session.get("loggedin") and session.get("role") == "ADMIN"):
        return redirect(url_for("login"))

    first_name = (request.form.get("first_name") or "").strip()
    last_name  = (request.form.get("last_name") or "").strip()
    email      = (request.form.get("email") or "").strip()
    password   = (request.form.get("password") or "")
    role       = (request.form.get("role") or "CUSTOMER").strip().upper()

    if role not in ("CUSTOMER", "ADMIN"):
        role = "CUSTOMER"

    if not first_name or not last_name or not email or len(password) < 8:
        flash("Please fill all fields (password min 8 chars).", "danger")
        return redirect(url_for("admin_users"))
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT user_id FROM users WHERE email=%s", (email,))
    if cursor.fetchone():
        cursor.close()
        db.close()
        flash("That email already exists.", "warning")
        return redirect(url_for("admin_users"))

    hashed = generate_password_hash(password, method="pbkdf2:sha256")

    cursor2 = db.cursor()
    cursor2.execute("""
        INSERT INTO users (role, first_name, last_name, email, password_hash, is_active)
        VALUES (%s, %s, %s, %s, %s, 1)
    """, (role, first_name, last_name, email, hashed))
    db.commit()
    cursor2.close()
    db.close()
    cursor.close()
    db.close()

    flash("User created successfully.", "success")
    return redirect(url_for("admin_users"))

@app.route("/admin/users/<int:user_id>/toggle", methods=["POST"])
def admin_users_toggle(user_id):
    if not (session.get("loggedin") and session.get("role") == "ADMIN"):
        return redirect(url_for("login"))

    if user_id == session.get("user_id"):
        flash("You cannot deactivate your own account.", "warning")
        return redirect(url_for("admin_users"))

    action = (request.form.get("action") or "").lower()
    new_value = 1 if action == "activate" else 0
    db = get_db()
    cursor = db.cursor()
    cursor.execute("UPDATE users SET is_active=%s WHERE user_id=%s", (new_value, user_id))
    db.commit()
    cursor.close()
    db.close()

    flash("User status updated.", "success")
    return redirect(url_for("admin_users"))

@app.route("/admin/users/<int:user_id>/delete", methods=["POST"])
def admin_users_delete(user_id):
    if not (session.get("loggedin") and session.get("role") == "ADMIN"):
        return redirect(url_for("login"))

    if user_id == session.get("user_id"):
        flash("You cannot delete your own account.", "warning")
        return redirect(url_for("admin_users"))

    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("DELETE FROM users WHERE user_id=%s", (user_id,))
        db.commit()
        cursor.close()
        db.close()
        flash("User deleted.", "success")
    except Exception as e:
        flash(f"Cannot delete this user (they may have bookings). Deactivate instead. ({e})", "warning")

    return redirect(url_for("admin_users"))

@app.route('/admin/staffs')
def admin_staffs():
    if not (session.get('loggedin') and session.get('role') == 'ADMIN'):
        return redirect(url_for('login'))

    q = (request.args.get("q") or "").strip()
    like = f"%{q}%"
    db = get_db()
    cursor = db.cursor(dictionary=True)

    if q:
        cursor.execute("""
          SELECT user_id, first_name, last_name, email, role, is_active
          FROM users
          WHERE role='ADMIN' AND (first_name LIKE %s OR last_name LIKE %s OR email LIKE %s)
          ORDER BY user_id DESC
        """, (like, like, like))
    else:
        cursor.execute("""
          SELECT user_id, first_name, last_name, email, role, is_active
          FROM users
          WHERE role='ADMIN'
          ORDER BY user_id DESC
        """)
    staffs = cursor.fetchall()
    cursor.close()
    db.close()

    return render_template("admin/admin_staffs.html", staffs=staffs)


@app.route('/admin/rooms')
def admin_rooms():
    if not (session.get('loggedin') and session.get('role') == 'ADMIN'):
        return redirect(url_for('login'))

    q = (request.args.get("q") or "").strip().upper()
    db = get_db()
    cursor = db.cursor(dictionary=True)

    if q:
        cursor.execute("""
          SELECT room_type_id, code, max_guests, base_multiplier, second_guest_multiplier
          FROM room_types
          WHERE code LIKE %s
          ORDER BY room_type_id
        """, (f"%{q}%",))
    else:
        cursor.execute("""
          SELECT room_type_id, code, max_guests, base_multiplier, second_guest_multiplier
          FROM room_types
          ORDER BY room_type_id
        """)
    room_types = cursor.fetchall()

    cursor.execute("SELECT COUNT(*) AS n FROM room_types")
    room_types_count = cursor.fetchone()["n"]

    cursor.execute("SELECT COALESCE(MAX(max_guests),0) AS m FROM room_types")
    max_guests_supported = cursor.fetchone()["m"]

    cursor.execute("SELECT COUNT(*) AS n FROM hotel_room_inventory")
    inventory_rows = cursor.fetchone()["n"]

    cursor.close()
    db.close()

    return render_template("admin/admin_rooms.html",
                           room_types=room_types,
                           room_types_count=room_types_count,
                           max_guests_supported=max_guests_supported,
                           inventory_rows=inventory_rows)

@app.route('/admin/reservations')
def admin_reservations():
    if not (session.get('loggedin') and session.get('role') == 'ADMIN'):
        return redirect(url_for('login'))

    q = (request.args.get("q") or "").strip()
    like = f"%{q}%"
    db = get_db()
    cursor = db.cursor(dictionary=True)

    base_sql = """
      SELECT b.booking_id, b.booking_code, b.booking_status, b.created_at,
             b.check_in, b.check_out, b.total_gbp,
             u.first_name, u.last_name, u.email,
             h.hotel_name, c.name AS city
      FROM bookings b
      JOIN users u ON u.user_id=b.user_id
      JOIN hotels h ON h.hotel_id=b.hotel_id
      JOIN cities c ON c.city_id=h.city_id
    """
    params = []
    if q:
        base_sql += """
          WHERE b.booking_code LIKE %s
             OR u.email LIKE %s
             OR c.name LIKE %s
        """
        params = [like, like, like]

    base_sql += " ORDER BY b.created_at DESC LIMIT 200"
    cursor.execute(base_sql, params)
    bookings = cursor.fetchall()

    cursor.execute("SELECT COUNT(*) AS n FROM bookings")
    total_bookings = cursor.fetchone()["n"]
    cursor.execute("SELECT COUNT(*) AS n FROM bookings WHERE booking_status='CONFIRMED'")
    confirmed_bookings = cursor.fetchone()["n"]
    cursor.execute("SELECT COUNT(*) AS n FROM bookings WHERE booking_status='CANCELLED'")
    cancelled_bookings = cursor.fetchone()["n"]

    cursor.close()
    db.close()

    return render_template("admin/admin_reservations.html",
                           bookings=bookings,
                           total_bookings=total_bookings,
                           confirmed_bookings=confirmed_bookings,
                           cancelled_bookings=cancelled_bookings)

@app.route('/admin/analytics')
def admin_analytics():
    if not (session.get('loggedin') and session.get('role') == 'ADMIN'):
        return redirect(url_for('login'))
    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT COALESCE(SUM(total_gbp),0) AS revenue FROM bookings WHERE booking_status='CONFIRMED'")
    revenue_gbp = cursor.fetchone()["revenue"]

    cursor.execute("SELECT COUNT(*) AS n FROM bookings")
    bookings_count = cursor.fetchone()["n"]

    cursor.execute("SELECT COUNT(*) AS n FROM users WHERE is_active=1")
    active_users = cursor.fetchone()["n"]

    cursor.execute("SELECT COUNT(*) AS n FROM bookings WHERE booking_status='CANCELLED'")
    cancellations = cursor.fetchone()["n"]

    cursor.execute("""
      SELECT c.name AS city, COUNT(*) AS count
      FROM bookings b
      JOIN hotels h ON h.hotel_id=b.hotel_id
      JOIN cities c ON c.city_id=h.city_id
      WHERE b.booking_status='CONFIRMED'
      GROUP BY c.name
      ORDER BY count DESC
      LIMIT 6
    """)
    top_cities = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template("admin/admin_analytics.html",
                           revenue_gbp=revenue_gbp,
                           bookings_count=bookings_count,
                           active_users=active_users,
                           cancellations=cancellations,
                           top_cities=top_cities)


@app.route('/admin/reports')
def admin_reports():
    if not (session.get('loggedin') and session.get('role') == 'ADMIN'):
        return redirect(url_for('login'))
    return render_template("admin/admin_reports.html")

def get_setting(key, default=None):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT setting_value FROM site_settings WHERE setting_key=%s LIMIT 1", (key,))
    row = cursor.fetchone()
    cursor.close()
    db.close()
    return row["setting_value"] if row else default

def set_setting(key, value):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        INSERT INTO site_settings (setting_key, setting_value)
        VALUES (%s, %s)
        ON DUPLICATE KEY UPDATE setting_value=VALUES(setting_value)
    """, (key, value))
    db.commit()
    cursor.close()
    db.close()

@app.route("/admin/settings", methods=["GET", "POST"])
def admin_settings():
    if not (session.get("loggedin") and session.get("role") == "ADMIN"):
        return redirect(url_for("login"))

    if request.method == "POST":
        site_name = (request.form.get("site_name") or "").strip()
        base_currency = (request.form.get("base_currency") or "GBP").strip().upper()

        allowed = {"GBP", "USD", "EUR", "NRS"}
        if not site_name:
            flash("Site name cannot be empty.", "danger")
        elif base_currency not in allowed:
            flash("Invalid currency selected.", "danger")
        else:
            set_setting("site_name", site_name)
            set_setting("base_currency", base_currency)
            flash("Settings saved successfully.", "success")

        return redirect(url_for("admin_settings"))

    settings = {
        "site_name": get_setting("site_name", "World Hotels"),
        "base_currency": get_setting("base_currency", "GBP"),
    }
    return render_template("admin/admin_settings.html", settings=settings)

@app.route("/season-pricing")
def season_pricing():
    checkin = request.args.get("checkin")
    season = None

    if checkin:
        y, m, d = map(int, checkin.split("-"))
        season = "peak" if (4 <= m <= 8 or m in (11, 12)) else "off_peak"

    rates = [
        {"city": "Aberdeen", "capacity": 90, "peak": 140, "off_peak": 70},
        {"city": "Belfast", "capacity": 80, "peak": 130, "off_peak": 70},
        {"city": "Birmingham", "capacity": 110, "peak": 150, "off_peak": 75},
        {"city": "Bristol", "capacity": 100, "peak": 140, "off_peak": 70},
        {"city": "Cardiff", "capacity": 90, "peak": 130, "off_peak": 70},
        {"city": "Edinburgh", "capacity": 120, "peak": 160, "off_peak": 80},
        {"city": "Glasgow", "capacity": 140, "peak": 150, "off_peak": 75},
        {"city": "London", "capacity": 160, "peak": 200, "off_peak": 100},
        {"city": "Manchester", "capacity": 150, "peak": 180, "off_peak": 90},
        {"city": "New Castle", "capacity": 90, "peak": 120, "off_peak": 70},
        {"city": "Norwich", "capacity": 90, "peak": 130, "off_peak": 70},
        {"city": "Nottingham", "capacity": 110, "peak": 130, "off_peak": 70},
        {"city": "Oxford", "capacity": 90, "peak": 180, "off_peak": 90},
        {"city": "Plymouth", "capacity": 80, "peak": 180, "off_peak": 90},
        {"city": "Swansea", "capacity": 70, "peak": 130, "off_peak": 70},
        {"city": "Bournemouth", "capacity": 90, "peak": 130, "off_peak": 70},
        {"city": "Kent", "capacity": 100, "peak": 140, "off_peak": 80},
    ]

    return render_template("season_pricing.html", rates=rates, season=season, checkin=checkin)

def season_from_checkin(checkin_str: Optional[str]):
    if not checkin_str:
        return None
    try:
        m = datetime.strptime(checkin_str, "%Y-%m-%d").month
        return "peak" if (4 <= m <= 8 or m in (11, 12)) else "off_peak"
    except ValueError:
        return None

def parse_checkin_arg(checkin_str: Optional[str]):
    """
    Accepts YYYY-MM-DD (from <input type="date">).
    Returns a datetime.date or None.
    """
    if not checkin_str:
        return None
    try:
        return datetime.strptime(checkin_str, "%Y-%m-%d").date()
    except ValueError:
        return None

def is_peak_season(d: date):
    return (4 <= d.month <= 8) or (d.month in (11, 12))

def is_peak_from_checkin(checkin_str: Optional[str]) -> bool:
    if not checkin_str:
        m = date.today().month
        return (4 <= m <= 8) or (m in (11, 12))

    try:
        d = datetime.strptime(checkin_str, "%Y-%m-%d").date()
        m = d.month
        return (4 <= m <= 8) or (m in (11, 12))
    except ValueError:
        m = date.today().month
        return (4 <= m <= 8) or (m in (11, 12))

def resolve_season(checkin_str: Optional[str], season_override: str) -> bool:
    if season_override == "peak":
        return True
    if season_override == "off_peak":
        return False
    return is_peak_from_checkin(checkin_str)

@app.route("/admin/bookings/<int:booking_id>/cancel", methods=["POST"])
def admin_cancel_booking(booking_id):
    if not (session.get("loggedin") and session.get("role") == "ADMIN"):
        return redirect(url_for("login"))
    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        UPDATE bookings
        SET booking_status = 'CANCELLED'
        WHERE booking_id = %s AND booking_status <> 'CANCELLED'
    """, (booking_id,))
    db.commit()

    cursor.close()
    db.close()

    flash("Booking cancelled (admin).", "success")
    return redirect(url_for("admin_reservations"))  


@app.route("/admin/bookings/<int:booking_id>/delete", methods=["POST"])
def admin_delete_booking(booking_id):
    if not (session.get("loggedin") and session.get("role") == "ADMIN"):
        return redirect(url_for("login"))
    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM bookings WHERE booking_id = %s", (booking_id,))
    db.commit()

    cursor.close()
    db.close()

    flash("Booking deleted permanently (admin).", "success")
    return redirect(url_for("admin_reservations"))

@app.route("/dismiss-demo-notice", methods=["POST"])
def dismiss_demo_notice():
    session["hide_demo_notice"] = True
    return ("", 204)

@app.route("/show-demo-notice")
def show_demo_notice():
    session.pop("hide_demo_notice", None)
    return redirect(request.referrer or url_for("index"))

@app.route("/db-test")
def db_test():
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT DATABASE(), @@hostname, @@port")
    row = cur.fetchone()
    cur.close()
    db.close()
    return f"Connected to DB={row[0]}, host={row[1]}, port={row[2]}"

if __name__== '__main__':
    app.run(debug=True)