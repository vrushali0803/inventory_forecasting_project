from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify
import re

from db import get_db_connection
from rapidfuzz import process
from services.advanced_forecasting import predict_demand
from services.crop_knowledge import CROP_INFO


distributor_bp = Blueprint("distributor", __name__)


def is_logged_in():
    return session.get('user_id') and session.get('role') == 'distributor'

# ================= sign-up =================

@distributor_bp.route('/signup', methods=['GET', 'POST'])
def distributor_signup():

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form.get('confirm_password')
        email = request.form['email']
        region = request.form['region']

        conn = get_db_connection()
        cur = conn.cursor()

        # check existing user
        cur.execute("SELECT id FROM users WHERE username=%s", (username,))
        if cur.fetchone():
            cur.close(); conn.close()
            return render_template("distributor_signup.html", error_field="username")

        # password checks
        if password != confirm_password:
            cur.close(); conn.close()
            return render_template("distributor_signup.html", error_field="confirm_password")

        if len(password) < 8:
            cur.close(); conn.close()
            return render_template("distributor_signup.html", error_field="password")

        # insert
        cur.execute("""
            INSERT INTO users (username, password, email, role, region)
            VALUES (%s, %s, %s, 'distributor', %s)
        """, (username, password, email, region))

        conn.commit()
        cur.close(); conn.close()

        return redirect(url_for('auth.distributor_login'))

    return render_template("distributor_signup.html")

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
from services.advanced_forecasting import predict_demand


@distributor_bp.route('/dashboard')
def marketplace():

    if not is_logged_in():
        return redirect(url_for('auth.distributor_login'))

    distributor_id = session['user_id']

    conn = get_db_connection()
    cur = conn.cursor()

    # ✅ GET REGION
    cur.execute("SELECT region FROM users WHERE id=%s", (distributor_id,))
    region_data = cur.fetchone()
    region = region_data[0] if region_data and region_data[0] else None

    # ✅ LOAD PRODUCTS
    products = load_products()

    # ✅ CART COUNT
    cur.execute("""
        SELECT COUNT(*) FROM cart_items
        WHERE distributor_id=%s
    """, (distributor_id,))
    cart_count = cur.fetchone()[0]

    cur.close()
    conn.close()

    # ✅ ML LOGIC (OPTION B - CLEAN)
    if not region:
        recommended_crop = "Update Region"
        predicted_demand = 0
        demand_trend = "Unknown"
    else:
        try:
            prediction = predict_demand(region)

            # 🔥 FIXED KEYS
            recommended_crop = prediction.get("crop", "N/A")
            predicted_demand = prediction.get("demand", 0)

            if predicted_demand > 800:
                demand_trend = "High 📈"
            elif predicted_demand > 400:
                demand_trend = "Moderate 📊"
            else:
                demand_trend = "Low 📉"

        except Exception as e:
            print("ML ERROR:", e)
            recommended_crop = "Data not available"
            predicted_demand = 0
            demand_trend = "Unknown"

    return render_template(
        "distributor_home.html",
        products=products,
        username=session.get('username'),
        email=session.get('email'),
        cart_count=cart_count,
        recommended_crop=recommended_crop,
        demand_trend=demand_trend,
        demand_units=predicted_demand,
        region=region
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

    # Cart Items
    cur.execute("""
        SELECT c.product_id,
               c.quantity,
               p.price,
               p.crop
        FROM cart_items c
        JOIN products p
        ON c.product_id = p.id
        WHERE c.distributor_id = %s
    """, (distributor_id,))

    items = cur.fetchall()

    if not items:
        cur.close()
        conn.close()
        return "Cart is empty!"

    total = 0
    total_quantity = 0

    for item in items:
        total += int(item[1]) * int(item[2])
        total_quantity += int(item[1])

    # Region
    cur.execute("""
        SELECT region
        FROM users
        WHERE id=%s
    """, (distributor_id,))

    region_row = cur.fetchone()

    region = region_row[0] if region_row else "Unknown"

    # First product name
    first_crop = items[0][3]

    # Insert Order
    cur.execute("""
        INSERT INTO orders
        (
            distributor_id,
            total,
            region,
            product_name,
            quantity,
            created_at
        )
        VALUES
        (
            %s,%s,%s,%s,%s,NOW()
        )
        RETURNING id
    """, (
        distributor_id,
        total,
        region,
        first_crop,
        total_quantity
    ))

    order_id = cur.fetchone()[0]

    # Insert Order Items
    for item in items:

        product_id = item[0]
        quantity = int(item[1])
        price = float(item[2])

        cur.execute("""
            INSERT INTO order_items
            (
                order_id,
                product_id,
                quantity,
                price,
                region
            )
            VALUES
            (
                %s,%s,%s,%s,%s
            )
        """, (
            order_id,
            product_id,
            quantity,
            price,
            region
        ))

    # Clear Cart
    cur.execute("""
        DELETE FROM cart_items
        WHERE distributor_id=%s
    """, (distributor_id,))

    conn.commit()

    cur.close()
    conn.close()

    return render_template("order_success.html")
# ================= PROFILE =================
@distributor_bp.route('/profile', methods=['GET', 'POST'])
def profile():

    if not is_logged_in():
        return redirect(url_for('auth.distributor_login'))

    user_id = session.get('user_id')

    conn = get_db_connection()
    cur = conn.cursor()

    if request.method == 'POST':

        distributor_name = request.form['distributor_name']
        shop_name = request.form['shop_name']
        phone = request.form['phone']
        email = request.form['email']
        state = request.form['state']
        district = request.form['district']
        address = request.form['address']
        gst_number = request.form['gst_number']
        pincode = request.form['pincode']

        cur.execute("""
            UPDATE users
            SET
                distributor_name=%s,
                shop_name=%s,
                phone=%s,
                email=%s,
                state=%s,
                district=%s,
                address=%s,
                gst_number=%s,
                pincode=%s
            WHERE id=%s
        """, (
            distributor_name,
            shop_name,
            phone,
            email,
            state,
            district,
            address,
            gst_number,
            pincode,
            user_id
        ))

        conn.commit()

    cur.execute("""
        SELECT *
        FROM users
        WHERE id=%s
    """, (user_id,))

    user = cur.fetchone()

    cur.close()
    conn.close()

    return render_template(
        'profile.html',
        user=user
    )
# ================= SECURITY =================
@distributor_bp.route('/security', methods=['GET', 'POST'])
def security():

    if not is_logged_in():
        return redirect(url_for('auth.distributor_login'))

    if request.method == 'POST':

        print("USER ID =", session.get('user_id'))

        new_password = request.form.get('new_password')

        print("NEW PASSWORD =", new_password)

        if not new_password:
            return "Password cannot be empty"

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            UPDATE users
            SET password=%s
            WHERE id=%s
        """, (new_password, session['user_id']))

        conn.commit()

        cur.close()
        conn.close()

        return "<h3>Password Updated Successfully</h3>"

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

#===============================AI bot=======================
@distributor_bp.route('/chatbot', methods=['POST'])
def chatbot():
    try:
        data = request.get_json()
        user_msg = data.get("message", "").lower().strip()

        distributor_id = session.get("user_id")

        if not distributor_id:
            return jsonify({
                "reply": "🔒 Please login first."
            })

        conn = get_db_connection()
        cur = conn.cursor()

        # =====================================
        # USER REGION
        # =====================================

        cur.execute(
            "SELECT region FROM users WHERE id=%s",
            (distributor_id,)
        )

        region_data = cur.fetchone()
        region = region_data[0] if region_data else None

        if not region:
            cur.close()
            conn.close()
            return jsonify({
                "reply": "📍 Please update your region first."
            })

        # =====================================
        # PRODUCTS
        # =====================================

        cur.execute("""
            SELECT crop, variety, season, price, category
            FROM products
        """)

        products = cur.fetchall()

        crops = [
            row[0].lower()
            for row in products
            if row[0]
        ]

        total_products = len(products)

        # =====================================
        # GREETING
        # =====================================

        if any(word in user_msg for word in [
            "hi", "hello", "hey", "good morning", "good evening"
        ]):
            cur.close()
            conn.close()
            return jsonify({
                "reply": (
                    "👋 Welcome to BeejMitra AI Assistant\n\n"
                    "🌾 Crop Information\n"
                    "💰 Crop Pricing\n"
                    "📦 Inventory Analysis\n"
                    "📈 Demand Forecasting\n"
                    "🏆 Sales Analytics\n\n"
                    "Try:\n\n"
                    "• Tell me about rice\n"
                    "• Price of lotus\n"
                    "• Show flowers\n"
                    "• Show fruits\n"
                    "• What should I stock?\n"
                    "• Best selling crop\n"
                    "• Cheapest crop"
                )
            })

        # =====================================
        # HELP
        # =====================================

        if "help" in user_msg or "what can you do" in user_msg:
            cur.close()
            conn.close()
            return jsonify({
                "reply": (
                    "🤖 I can help you with:\n\n"
                    "🌾 Crop Information\n"
                    "💰 Product Prices\n"
                    "📦 Inventory Details\n"
                    "📈 Demand Forecasting\n"
                    "🏆 Sales Analytics\n\n"
                    "Examples:\n\n"
                    "• Tell me about cotton\n"
                    "• Price of rose\n"
                    "• Show flowers\n"
                    "• Show kharif crops\n"
                    "• What should I stock?\n"
                    "• Cheapest crop\n"
                    "• Costliest crop\n"
                    "• Crops under 500\n"
                    "• Best selling crop"
                )
            })
        # =====================================
        # INVENTORY
        # =====================================

        if "inventory" in user_msg or "products" in user_msg:

            crop_list = ", ".join(
                sorted(set([row[0] for row in products]))
            )

            cur.close()
            conn.close()

            return jsonify({
                "reply":
                f"""📦 Inventory Summary

         Total Products: {total_products}

         Available Crops:

         {crop_list}
         """
              })
        # =====================================
        # DEMAND FORECAST
        # =====================================

        if any(word in user_msg for word in [
            "stock", "recommend", "forecast", "demand",
            "what should i", "suggest"
        ]):
            try:
                prediction = predict_demand(region)
                crop = prediction.get("crop", "N/A")
                demand = prediction.get("demand", 0)
                cur.close()
                conn.close()
                return jsonify({
                    "reply": (
                        f"📈 Demand Forecast for {region}\n\n"
                        f"🌾 Recommended Crop: {crop}\n"
                        f"📦 Predicted Demand: {demand} units"
                    )
                })
            except Exception as e:
                print("FORECAST ERROR:", e)
                cur.close()
                conn.close()
                return jsonify({
                    "reply": "⚠️ Forecast data not available."
                })

        # =====================================
        # PRICE QUERY
        # =====================================

        if "price" in user_msg or "cost" in user_msg:

            for row in products:

                crop = row[0].lower()

                if crop in user_msg:

                    cur.close()
                    conn.close()

                    return jsonify({
                        "reply":
                        f"""💰 {row[0]}
 
         🌱 Variety: {row[1]}
         📅 Season: {row[2]}
         💵 Price: ₹{row[3]}
         📂 Category: {row[4]}
         """
                      })
        # =====================================
        # CROP INFO (exact match)
        # =====================================

        for crop, info in CROP_INFO.items():
            if crop in user_msg:
                cur.close()
                conn.close()
                return jsonify({
                    "reply": (
                        f"🌾 {crop.title()}\n\n"
                        f"📅 Season: {info['season']}\n"
                        f"💧 Water: {info['water']}\n"
                        f"🌱 Soil: {info['soil']}\n"
                        f"⏳ Duration: {info['duration']}"
                    )
                })

        # =====================================
        # CHEAPEST CROP
        # =====================================

        if "cheapest" in user_msg or "lowest price" in user_msg:
            cheapest = min(products, key=lambda x: float(x[3]))
            cur.close()
            conn.close()
            return jsonify({
                "reply": (
                    f"💰 Cheapest Crop\n\n"
                    f"🌾 Crop: {cheapest[0]}\n"
                    f"💵 Price: ₹{cheapest[3]}\n"
                    f"📂 Category: {cheapest[4]}"
                )
            })

        # =====================================
        # COSTLIEST CROP
        # =====================================

        if "costliest" in user_msg or "most expensive" in user_msg:
            expensive = max(products, key=lambda x: float(x[3]))
            cur.close()
            conn.close()
            return jsonify({
                "reply": (
                    f"💎 Costliest Crop\n\n"
                    f"🌾 Crop: {expensive[0]}\n"
                    f"💵 Price: ₹{expensive[3]}\n"
                    f"📂 Category: {expensive[4]}"
                )
            })

        # =====================================
        # AVERAGE PRICE
        # =====================================

        if "average price" in user_msg:
            avg_price = round(
                sum(float(row[3]) for row in products) / len(products), 2
            )
            cur.close()
            conn.close()
            return jsonify({
                "reply": f"📊 Average Product Price: ₹{avg_price}"
            })

        # =====================================
        # CROPS UNDER BUDGET
        # =====================================

        budget_match = re.search(r'under\s+(\d+)', user_msg)

        if budget_match:
            budget = int(budget_match.group(1))
            result = [
                f"{row[0]} (₹{row[3]})"
                for row in products
                if float(row[3]) <= budget
            ]
            cur.close()
            conn.close()
            if result:
                return jsonify({
                    "reply": f"💰 Crops Under ₹{budget}\n\n" + "\n".join(result)
                })

        # =====================================
        # PRICE RANGE SEARCH
        # =====================================

        range_match = re.search(r'between\s+(\d+)\s+and\s+(\d+)', user_msg)

        if range_match:
            min_price = int(range_match.group(1))
            max_price = int(range_match.group(2))
            result = [
                f"{row[0]} (₹{float(row[3])})"
                for row in products
                if min_price <= float(row[3]) <= max_price
            ]
            cur.close()
            conn.close()
            if result:
                return jsonify({
                    "reply": f"💰 Products Between ₹{min_price} and ₹{max_price}\n\n" + "\n".join(result)
                })
        # =====================================
        # SEASON SEARCH
        # =====================================

        season_keywords = [
            "kharif",
            "rabi",
            "winter",
            "all season",
            "all seasons"
        ]

        for season in season_keywords:

           if season in user_msg:

               matched = []

               for row in products:

                   if row[2] and season.lower() in row[2].lower():
                       matched.append(row[0])

               cur.close()
               conn.close()

               if matched:
                  return jsonify({
                      "reply":
                      f"📅 {season.title()} Crops:\n\n" +
                      "\n".join(sorted(set(matched)))
                   })

        # =====================================
        # CATEGORY SEARCH
        # =====================================

        categories = [
           "flowers",
           "fruits",
           "vegetables",
           "field crops"
        ]

        for category in categories:

            if category in user_msg:

                result = []
 
                for row in products:

                    if row[4] and row[4].strip().lower() == category:
                        result.append(row[0])

                cur.close()
                conn.close()

                if result:
                    return jsonify({
                       "reply":
                        f"🌱 {category.title()}:\n\n" +
                        "\n".join(sorted(set(result)))
                     })
        # =====================================
        # FLOWER COUNT
        # =====================================

        if "how many flowers" in user_msg:
            count = len([
                row for row in products
                if row[4] and row[4].lower() == "flowers"
            ])
            cur.close()
            conn.close()
            return jsonify({
                "reply": f"🌸 Total Flower Products: {count}"
            })

        # =====================================
        # BEST SELLING CROP
        # =====================================

        if "best selling" in user_msg:
            cur.execute("""
                SELECT product_name, COUNT(*)
                FROM orders
                GROUP BY product_name
                ORDER BY COUNT(*) DESC
                LIMIT 1
            """)
            best = cur.fetchone()
            cur.close()
            conn.close()
            if best:
                return jsonify({
                    "reply": (
                        f"🏆 Best Selling Crop\n\n"
                        f"🌾 {best[0]}\n"
                        f"📦 Orders: {best[1]}"
                    )
                })

        # =====================================
        # TOP 3 CROPS
        # =====================================

        if "top 3 crops" in user_msg or "top crops" in user_msg:
            cur.execute("""
                SELECT product_name, COUNT(*)
                FROM orders
                GROUP BY product_name
                ORDER BY COUNT(*) DESC
                LIMIT 3
            """)
            rows = cur.fetchall()
            cur.close()
            conn.close()
            if rows:
                msg = "📈 Top Selling Crops\n\n"
                for i, row in enumerate(rows, start=1):
                    msg += f"{i}. {row[0]} ({row[1]} orders)\n"
                return jsonify({"reply": msg})

        # =====================================
        # FUZZY MATCH
        # =====================================

        result = process.extractOne(user_msg, crops)

        if result:
            best_match = result[0]
            score = result[1]

            if score > 70:
                crop = best_match.lower()
                if crop in CROP_INFO:
                    info = CROP_INFO[crop]
                    cur.close()
                    conn.close()
                    return jsonify({
                        "reply": (
                            f"🌾 {crop.title()}\n\n"
                            f"📅 Season: {info['season']}\n"
                            f"💧 Water: {info['water']}\n"
                            f"🌱 Soil: {info['soil']}\n"
                            f"⏳ Duration: {info['duration']}"
                        )
                    })

        cur.close()
        conn.close()

        return jsonify({
            "reply": (
                "🤖 Sorry, I didn't understand.\n\n"
                "Try:\n\n"
                "• Tell me about rice\n"
                "• Price of rose\n"
                "• Cheapest crop\n"
                "• Costliest crop\n"
                "• Best selling crop\n"
                "• Top 3 crops\n"
                "• What should I stock?"
            )
        })

    except Exception as e:
        print("CHATBOT ERROR:", e)
        return jsonify({
            "reply": "⚠️ Something went wrong."
        })

