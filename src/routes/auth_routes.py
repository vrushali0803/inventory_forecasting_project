from flask import Blueprint, render_template, request, redirect, url_for, session
from db import get_db_connection

auth_bp = Blueprint('auth', __name__)

# ================= ADMIN LOGIN =================
@auth_bp.route('/admin-login', methods=['GET', 'POST'])
def admin_login():

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT id, username, password, role
            FROM users
            WHERE username = %s AND role = 'company'
        """, (username,))

        user = cur.fetchone()

        cur.close()
        conn.close()

        if user and user[2] == password:
            session['user_id'] = user[0]
            session['role'] = user[3]

            # IMPORTANT → match your existing code
            return redirect(url_for('admin.admin_dashboard'))

        else:
            return "Invalid Admin Credentials"

    return render_template('admin_login.html')


# ================= DISTRIBUTOR LOGIN =================
@auth_bp.route('/distributor_login', methods=['GET', 'POST'])
def distributor_login():

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT id, username, password, role
            FROM users
            WHERE username = %s AND role = 'distributor'
        """, (username,))

        user = cur.fetchone()

        cur.close()
        conn.close()

        if user and user[2] == password:
            session['user_id'] = user[0]
            session['username'] = user[1]
            session['role'] = user[3]

            return redirect(url_for('distributor.marketplace'))

        else:
            return "Invalid Login"

    return render_template('distributor_login.html')


# ================= DISTRIBUTOR SIGNUP =================
@auth_bp.route('/distributor-signup', methods=['GET', 'POST'])
def distributor_signup():

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form.get('confirm_password')
        email = request.form['email']
        region = request.form['region']

        conn = get_db_connection()
        cur = conn.cursor()

        # 🔒 Username check
        cur.execute("SELECT id FROM users WHERE username=%s", (username,))
        if cur.fetchone():
            cur.close()
            conn.close()
            return render_template("distributor_signup.html", error_field="username")

        # 🔒 Password validation
        if password != confirm_password:
            cur.close()
            conn.close()
            return render_template("distributor_signup.html", error_field="confirm_password")

        if len(password) < 8:
            cur.close()
            conn.close()
            return render_template("distributor_signup.html", error_field="password")

        # 🔥 INSERT USER
        cur.execute("""
            INSERT INTO users (username, password, email, role, region)
            VALUES (%s, %s, %s, 'distributor', %s)
        """, (username, password, email, region))

        conn.commit()
        cur.close()
        conn.close()

        return redirect(url_for('auth.distributor_login'))

    return render_template("distributor_signup.html")

# ================= LOGOUT =================
@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('landing_page'))