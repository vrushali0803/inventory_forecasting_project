from flask import Blueprint, render_template, request, redirect, url_for, session
from db import get_db_connection

distributor_bp = Blueprint("distributor", __name__)

# ================= AUTH CHECK =================
def is_logged_in():
    return session.get('user_id') and session.get('role') == 'distributor'


# ================= LOAD PRODUCTS =================
def load_products():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, crop, variety, image_path, price, category
        FROM products
    """)

    rows = cur.fetchall()

    products = []
    for row in rows:
        products.append({
            "id": row[0],
            "crop": row[1],
            "variety": row[2],
            "image_path": row[3],
            "price": row[4],
            "category": (row[5] or "").strip().lower()
        })

    cur.close()
    conn.close()
    return products


# ================= MARKETPLACE =================
@distributor_bp.route('/dashboard')
def marketplace():

    if not is_logged_in():
        return redirect(url_for('auth.distributor_login'))

    products = load_products()

    # 🔥 CART BADGE COUNT
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT COUNT(*) FROM cart_items
        WHERE distributor_id=%s
    """, (session['user_id'],))

    cart_count = cur.fetchone()[0]

    cur.close()
    conn.close()

    return render_template(
        "distributor_home.html",
        products=products,
        username=session.get('username'),
        email=session.get('email'),
        cart_count=cart_count
    )


# ================= ADD TO CART =================
@distributor_bp.route('/add-to-cart', methods=['POST'])
def add_to_cart():

    if not is_logged_in():
        return redirect(url_for('auth.distributor_login'))

    distributor_id = session['user_id']
    product_id = request.form.get('product_id')
    quantity = int(request.form.get('quantity', 1))

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, quantity FROM cart_items
        WHERE distributor_id=%s AND product_id=%s
    """, (distributor_id, product_id))

    existing = cur.fetchone()

    if existing:
        cur.execute("""
            UPDATE cart_items
            SET quantity=%s
            WHERE id=%s
        """, (existing[1] + quantity, existing[0]))
    else:
        cur.execute("""
            INSERT INTO cart_items (distributor_id, product_id, quantity)
            VALUES (%s, %s, %s)
        """, (distributor_id, product_id, quantity))

    conn.commit()
    cur.close()
    conn.close()

    return redirect(url_for('distributor.marketplace'))


# ================= VIEW CART =================
@distributor_bp.route('/cart')
def view_cart():

    if not is_logged_in():
        return redirect(url_for('auth.distributor_login'))

    distributor_id = session['user_id']

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT p.id, p.variety, p.crop, p.price, c.quantity, p.image_path
        FROM cart_items c
        JOIN products p ON c.product_id = p.id
        WHERE c.distributor_id = %s
    """, (distributor_id,))

    items = cur.fetchall()
   
         
    # ✅ Convert Decimal → int (CRITICAL FIX)
    clean_items = []
    for item in items:
       clean_items.append((
           item[0],                 # id
           item[1],                 # variety
           item[2],                 # crop
           int(item[3]),            # price FIXED
           int(item[4]),            # quantity
           item[5]                  # image
      ))

    # ✅ calculate total
    total = 0
    for item in clean_items:
          total += item[3] * item[4]
    cur.close()
    conn.close()

    return render_template("cart.html", items=clean_items, total=total)

# ================= REMOVE ITEM =================
@distributor_bp.route('/remove-from-cart/<int:item_id>')
def remove_from_cart(item_id):

    if not is_logged_in():
        return redirect(url_for('auth.distributor_login'))

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("DELETE FROM cart_items WHERE id=%s", (item_id,))
    conn.commit()

    cur.close()
    conn.close()

    return redirect(url_for('distributor.view_cart'))

#===================Update_Cart===================
@distributor_bp.route('/update-cart/<product_id>/<action>')
def update_cart(product_id, action):

    if not is_logged_in():
        return redirect(url_for('auth.distributor_login'))

    distributor_id = session['user_id']

    conn = get_db_connection()
    cur = conn.cursor()

    if action == "inc":
        cur.execute("""
            UPDATE cart_items
            SET quantity = quantity + 1
            WHERE distributor_id=%s AND product_id=%s
        """, (distributor_id, product_id))

    elif action == "dec":
        cur.execute("""
            UPDATE cart_items
            SET quantity = quantity - 1
            WHERE distributor_id=%s AND product_id=%s
        """, (distributor_id, product_id))

        cur.execute("""
            DELETE FROM cart_items
            WHERE distributor_id=%s AND product_id=%s AND quantity<=0
        """, (distributor_id, product_id))

    conn.commit()
    cur.close()
    conn.close()

    return redirect(url_for('distributor.view_cart'))


# ================= CHECKOUT =================
@distributor_bp.route('/checkout')
def checkout():
    if not is_logged_in():
        return redirect(url_for('auth.distributor_login'))

    return render_template("payment.html")

# ================= PLACE ORDER =================
@distributor_bp.route('/place-order', methods=['POST'])
def place_order():

    if not is_logged_in():
        return redirect(url_for('auth.distributor_login'))

    distributor_id = session['user_id']

    conn = get_db_connection()
    cur = conn.cursor()

    # 🛒 Get cart items
    cur.execute("""
        SELECT c.product_id, c.quantity, p.price
        FROM cart_items c
        JOIN products p ON c.product_id = p.id
        WHERE c.distributor_id = %s
    """, (distributor_id,))

    items = cur.fetchall()

    # ❌ Safety check
    if not items:
        return "Cart is empty!"

    # 💰 Calculate total
    total = 0
    for item in items:
        total += int(item[1]) * int(item[2])

    # 📍 Get region
    cur.execute("SELECT region FROM users WHERE id=%s", (distributor_id,))
    region = cur.fetchone()[0]

    # 🏷️ Get product name (first item only for display)
    product_id = items[0][0]

    cur.execute("""
        SELECT crop FROM products WHERE id=%s
    """, (product_id,))
    product_name = cur.fetchone()[0]

    # 📦 Insert order (🔥 FIXED created_at)
    cur.execute("""
        INSERT INTO orders (distributor_id, total, region, product_name, created_at)
        VALUES (%s, %s, %s, %s, NOW())
        RETURNING id
    """, (distributor_id, total, region, product_name))

    order_id = cur.fetchone()[0]

    # 📄 Insert order items
    for item in items:
        product_id = item[0]
        quantity = int(item[1])
        price = int(item[2])

        cur.execute("""
            INSERT INTO order_items (order_id, product_id, quantity, price, region)
            VALUES (%s, %s, %s, %s, %s)
        """, (order_id, product_id, quantity, price, region))

    # 🧹 Clear cart
    cur.execute("""
        DELETE FROM cart_items WHERE distributor_id=%s
    """, (distributor_id,))

    conn.commit()
    cur.close()
    conn.close()

    return render_template("order_success.html")

# ================= PROFILE =================
@distributor_bp.route('/profile')
def profile():

    if not is_logged_in():
        return redirect(url_for('auth.distributor_login'))

    return render_template(
        "profile.html",
        username=session.get('username'),
        email=session.get('email')
    )

# ================= SECURITY =================
@distributor_bp.route('/security', methods=['GET', 'POST'])
def security():
    
    
    if not is_logged_in():
        return redirect(url_for('auth.distributor_login'))


    if request.method == 'POST':
        new_password = request.form.get('password')

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            UPDATE users SET password=%s WHERE id=%s
        """, (new_password, session['user_id']))

        conn.commit()
        cur.close()
        conn.close()

        return "<h3>Password Updated</h3>"

    return render_template("security.html")


# ================= HELP =================
@distributor_bp.route('/help')
def help_page():
    
    
    if not is_logged_in():
        return redirect(url_for('auth.distributor_login'))

    return render_template("help.html")

# ================= DELETE ACCOUNT =================
@distributor_bp.route('/delete-account')
def delete_account():
   
    
    if not is_logged_in():
        return redirect(url_for('auth.distributor_login'))


    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("DELETE FROM users WHERE id=%s", (session['user_id'],))
    conn.commit()

    cur.close()
    conn.close()

    session.clear()

    return redirect(url_for('auth.distributor_login'))

#==================order======================
@distributor_bp.route('/orders')
def orders():

    if not is_logged_in():
        return redirect(url_for('auth.distributor_login'))

    distributor_id = session['user_id']

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT 
            o.id,
            o.total,
            o.region,
            o.created_at,
            p.variety,
            oi.quantity
        FROM orders o
        JOIN order_items oi ON o.id = oi.order_id
        JOIN products p ON oi.product_id = p.id
        WHERE o.distributor_id = %s
        ORDER BY o.id DESC
    """, (distributor_id,))

    orders = cur.fetchall()

    cur.close()
    conn.close()

    return render_template("orders.html", orders=orders)
#===============================