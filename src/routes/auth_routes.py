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
            session['role'] = user[3]

            return redirect(url_for('distributor.marketplace'))

        else:
            return "Invalid Login"

    return render_template('distributor_login.html')


# ================= LOGOUT =================
@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('landing_page'))