from flask import Flask, render_template, request, redirect, url_for, session, make_response
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer
from werkzeug.security import generate_password_hash, check_password_hash

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
    return render_template("index.html")

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


@app.route('/hotels')
def hotels():
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT c.name AS city, h.hotel_name
        FROM hotels h
        JOIN cities c ON c.city_id = h.city_id
        WHERE h.is_active = 1
        ORDER BY c.name
    """)
    hotels_list = cursor.fetchall()
    cursor.close()

    # City -> image filename (put these files in static/images/hotels/)
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
        "New Castle": "newcastle.jpg",   # IMPORTANT: no space in filename
        "Norwich": "norwich.jpg",
        "Nottingham": "nottingham.jpg",
        "Oxford": "oxford.jpg",
        "Plymouth": "plymouth.jpg",
        "Swansea": "swansea.jpg",
        "Bournemouth": "bournemouth.jpg",
        "Kent": "kent.jpg",
    }

    # Attach image path for each hotel (fallback to default.jpg)
    for h in hotels_list:
        filename = city_images.get(h["city"], "default.jpg")
        h["img"] = f"images/hotels/{filename}"

    return render_template("hotels.html", hotels=hotels_list)



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
    if session.get('loggedin') and session.get('role') == 'CUSTOMER':
        cursor = db.cursor(dictionary=True)
        cursor.execute("""
            SELECT user_id, first_name, last_name, email
            FROM users
            WHERE user_id = %s
        """, (session['user_id'],))
        me = cursor.fetchone()
        return render_template('user/user_dashboard.html', me=me)

    return redirect(url_for('login'))


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

if __name__== '__main__':
    app.run(host="127.0.0.1", port=5000, debug=True)