from flask import Blueprint, render_template, session, redirect, url_for, request
from db import get_db_connection

admin_bp = Blueprint('admin', __name__)

# ================= ADMIN CHECK =================
def is_admin():
    return 'user_id' in session and session.get('role') == 'company'


# ================= DASHBOARD =================
@admin_bp.route('/dashboard')
def admin_dashboard():

    if not is_admin():
        return redirect(url_for('auth.admin_login'))

    conn = get_db_connection()
    cur = conn.cursor()

    # Total Orders
    cur.execute("SELECT COUNT(*) FROM orders")
    total_orders = cur.fetchone()[0]

    # Total Revenue
    cur.execute("""
        SELECT COALESCE(SUM(total), 0) FROM orders
    """)
    total_revenue = cur.fetchone()[0]

    # Total Demand
    cur.execute("""
        SELECT COALESCE(SUM(quantity), 0)
        FROM order_items
    """)
    total_demand = cur.fetchone()[0]

    # Top Crop
    cur.execute("""
        SELECT p.crop, SUM(oi.quantity) as total_qty
        FROM order_items oi
        JOIN products p ON oi.product_id = p.id
        GROUP BY p.crop
        ORDER BY total_qty DESC
        LIMIT 1
    """)
    top_crop_data = cur.fetchone()
    top_crop = top_crop_data[0] if top_crop_data else "N/A"

    cur.close()
    conn.close()

    return render_template(
        "dashboard.html",
        total_orders=total_orders,
        total_revenue=total_revenue,
        total_demand=total_demand,
        top_crop=top_crop
    )


# ================= ANALYTICS =================
@admin_bp.route('/analytics')
def analytics():

    if not is_admin():
        return redirect(url_for('auth.admin_login'))

    conn = get_db_connection()
    cur = conn.cursor()

    # Crop Demand
    cur.execute("""
        SELECT p.crop, SUM(oi.quantity)
        FROM order_items oi
        JOIN products p ON oi.product_id = p.id
        GROUP BY p.crop
    """)
    crop_data = cur.fetchall()

    crops = [row[0] for row in crop_data]
    crop_values = [row[1] for row in crop_data]


    # Region Demand
    cur.execute("""
        SELECT u.region, SUM(oi.quantity)
        FROM order_items oi
        JOIN orders o ON oi.order_id = o.id
        JOIN users u ON o.distributor_id = u.id
        GROUP BY u.region
    """)
    region_data = cur.fetchall()

    regions = [row[0] for row in region_data]
    region_values = [row[1] for row in region_data]


     # Monthly Demand Trend
    cur.execute("""
         SELECT 
            DATE_TRUNC('month', created_at) as month,
            SUM(total)
            FROM orders
            GROUP BY month
           ORDER BY month
    """) 

    monthly_data = cur.fetchall()

    months = [row[0].strftime('%b %Y') for row in monthly_data]
    values = [row[1] for row in monthly_data]
    

    cur.execute("""
    SELECT 
        CASE 
            WHEN EXTRACT(MONTH FROM created_at) IN (12,1,2) THEN 'Winter'
            WHEN EXTRACT(MONTH FROM created_at) IN (3,4,5) THEN 'Summer'
            WHEN EXTRACT(MONTH FROM created_at) IN (6,7,8,9) THEN 'Monsoon'
            ELSE 'Post-Monsoon'
        END AS season,
        SUM(total)
    FROM orders
    GROUP BY season
    """)

    season_data = cur.fetchall()

    seasons = [row[0] for row in season_data]
    season_values = [row[1] for row in season_data]

    cur.close()
    conn.close()
    
    print("MONTHS:", months)
    print("VALUES:", values)

    print("CROPS:", crops)
    print("CROP VALUES:", crop_values)

    print("REGIONS:", regions)
    print("REGION VALUES:", region_values)

    return render_template(
        "analytics.html",
         months=months,
         values=values,
         crops=crops,
         crop_values=crop_values,
         regions=regions,
         region_values=region_values,
         seasons=seasons,
         season_values=season_values
    )

#================forecasting======================

#================forecasting======================

from prophet import Prophet
import pandas as pd

@admin_bp.route('/forecast', methods=['GET', 'POST'])
def forecast():

    if not is_admin():
        return redirect(url_for('auth.admin_login'))

    prediction = None
    crop = None
    variety = None
    region = None
    insight = None

    conn = get_db_connection()
    cur = conn.cursor()

    # Dropdown data
    cur.execute("SELECT crop, variety FROM products")
    crops = cur.fetchall()

    if request.method == 'POST':

        crop_variety = request.form.get('crop_variety')
        region = request.form.get('region')

        if crop_variety:
            crop, variety = crop_variety.split('|')

            # 🔥 MONTHLY DEMAND DATA
            cur.execute("""
                SELECT 
                    DATE_TRUNC('month', o.created_at) as month,
                    SUM(oi.quantity)
                FROM order_items oi
                JOIN products p ON oi.product_id = p.id
                JOIN orders o ON oi.order_id = o.id
                JOIN users u ON o.distributor_id = u.id
                WHERE p.crop=%s AND p.variety=%s AND u.region=%s
                GROUP BY month
                ORDER BY month
            """, (crop, variety, region))

            data = cur.fetchall()

            # 🔥 CLEAN DATA
            clean_data = [(row[0], float(row[1])) for row in data]
            df = pd.DataFrame(clean_data, columns=["ds", "y"])

            prediction = 0

            # 🔥 PROPHET MODEL (UPGRADED)
            if len(df) >= 3:
                try:
                    model = Prophet(
                        yearly_seasonality=True,
                        weekly_seasonality=False,
                        daily_seasonality=False
                    )

                    model.fit(df)

                    # Predict next 1 month
                    future = model.make_future_dataframe(periods=1, freq='M')
                    forecast = model.predict(future)

                    prediction = int(forecast['yhat'].iloc[-1])

                except Exception as e:
                    print("PROPHET ERROR:", e)
                    prediction = int(df['y'].mean()) if not df.empty else 0
            else:
                prediction = int(df['y'].sum()) if not df.empty else 0


            # 🔥 SMART INSIGHT (UNCHANGED BUT CLEAN)
            if prediction == 0:
                insight = "⚠ No historical demand found."
            elif prediction < 20:
                insight = "📉 Low demand expected."
            elif prediction < 50:
                insight = "📊 Moderate demand expected."
            else:
                insight = "🔥 High demand expected! Increase production."


            # DEBUG
            print("DATA:", clean_data)
            print("PREDICTION:", prediction)


    cur.close()
    conn.close()

    return render_template(
        "forecast.html",
        crops=crops,
        prediction=prediction,
        crop=crop,
        variety=variety,
        region=region,
        insight=insight
    )
#=====================Recommendation==============================

@admin_bp.route('/recommendation')
def recommendation():
     
    if not is_admin():
        return redirect(url_for('auth.admin_login'))

    conn = get_db_connection()
    cur = conn.cursor()

    # 🔥 RECENT DEMAND (last 6 months)
    cur.execute("""
        SELECT 
            p.crop, 
            p.variety, 
            COALESCE(SUM(oi.quantity),0) as demand
        FROM products p
        LEFT JOIN order_items oi ON p.id = oi.product_id
        LEFT JOIN orders o ON oi.order_id = o.id
        LEFT JOIN users u ON o.distributor_id = u.id
        WHERE o.created_at >= NOW() - INTERVAL '6 months'
        GROUP BY p.crop, p.variety
    """)

    data = cur.fetchall()

    recommendations = []

    for row in data:
        crop, variety, demand = row

        # 🔥 SEASON DETECTION
        from datetime import datetime
        month = datetime.now().month

        if month in [6,7,8,9]:
            season = "Monsoon"
        elif month in [10,11]:
            season = "Post-Monsoon"
        elif month in [12,1,2]:
            season = "Winter"
        else:
            season = "Summer"

        # 🔥 SMART DECISION LOGIC
        if demand >= 80:
            action = "🚀 Increase Production"
            reason = "High recent demand"
        elif demand >= 30:
            action = "⚖️ Maintain Stock"
            reason = "Stable demand"
        else:
            action = "⚠️ Reduce Production"
            reason = "Low demand"

        # 🔥 SEASON BONUS LOGIC
        if season == "Monsoon" and crop in ["Rice","Maize","Cotton","Soybean"]:
            action = "🚀 Increase Production"
            reason = "Seasonal demand (Monsoon crops)"

        if season == "Winter" and crop in ["Wheat","Cauliflower","Cabbage"]:
            action = "🚀 Increase Production"
            reason = "Seasonal demand (Winter crops)"

        if season == "Summer" and crop in ["Watermelon","Muskmelon","Tomato","Chili"]:
            action = "🚀 Increase Production"
            reason = "Seasonal demand (Summer crops)"

        recommendations.append({
            "crop": crop,
            "variety": variety,
            "demand": demand,
            "action": action,
            "reason": reason,
            "season": season
        })

    cur.close()
    conn.close()

    return render_template("recommendation.html", data=recommendations)
#====================order===========================================
@admin_bp.route('/orders')
def view_orders():

    if not is_admin():
        return redirect(url_for('auth.admin_login')) 

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, distributor_id, product_name, total, region, created_at
        FROM orders
        ORDER BY created_at DESC
    """)

    orders = cur.fetchall()

    # Extra debug
    cur.execute("SELECT COUNT(*) FROM orders")
    print("TOTAL ROWS:", cur.fetchone())

    cur.close()
    conn.close()

    return render_template("admin_orders.html", orders=orders)

#=======================Profit=========================
@admin_bp.route('/profit')
def profit():

    if not is_admin():
        return redirect(url_for('auth.admin_login'))

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT 
            p.crop,
            p.variety,
            SUM(oi.quantity) as demand,
            AVG(p.price) as price
        FROM order_items oi
        JOIN products p ON oi.product_id = p.id
        GROUP BY p.crop, p.variety
    """)

    data = cur.fetchall()

    results = []

    for row in data:
        crop, variety, demand, price = row

        # 🔥 TYPE SAFETY (fixes Decimal error)
        demand = int(demand) if demand else 0
        price = float(price) if price else 0

        # 🔥 CALCULATIONS
        revenue = demand * price
        cost = revenue * 0.6   # 60% production cost assumption
        profit = revenue - cost

        # 🔥 PROFIT MARGIN
        margin = (profit / revenue * 100) if revenue > 0 else 0

        results.append({
            "crop": crop,
            "variety": variety,
            "demand": demand,
            "revenue": int(revenue),
            "profit": int(profit),
            "margin": round(margin, 2)
        })

    # 🔥 SORT BY PROFIT (high → low)
    results = sorted(results, key=lambda x: x['profit'], reverse=True)

    cur.close()
    conn.close()

    return render_template("profit.html", data=results)


#=======================Risk Indicator====================
@admin_bp.route('/risk')
def risk():

    if not is_admin():
        return redirect(url_for('auth.admin_login'))

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT 
            p.crop,
            p.variety,
            SUM(oi.quantity) as demand
        FROM order_items oi
        JOIN products p ON oi.product_id = p.id
        GROUP BY p.crop, p.variety
    """)

    data = cur.fetchall()

    risks = []

    for row in data:
        crop, variety, demand = row

        demand = int(demand) if demand else 0

        # 🔥 RISK LOGIC
        if demand > 4000:
            status = "⚠️ Overstock Risk"
            severity = "🟡 Medium"
            action = "Reduce production / increase marketing"
            score = 70

        elif demand < 500:
            status = "🚨 Shortage Risk"
            severity = "🔴 High"
            action = "Increase production immediately"
            score = 90

        else:
            status = "✅ Stable"
            severity = "🟢 Low"
            action = "Maintain current production"
            score = 30

        risks.append({
            "crop": crop,
            "variety": variety,
            "demand": demand,
            "status": status,
            "severity": severity,
            "action": action,
            "score": score
        })

    cur.close()
    conn.close()

    return render_template("risk.html", data=risks)