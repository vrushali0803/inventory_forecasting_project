from flask import Flask, render_template, session, redirect, url_for
import os
import time
# Import Blueprints
from routes.admin_routes import admin_bp
from routes.distributor_routes import distributor_bp
from routes.auth_routes import auth_bp

# Get base directory
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Static folder (outside src)
static_path = os.path.join(base_dir, "static")

# Initialize Flask
app = Flask(__name__, static_folder=static_path)

app.secret_key = "seed_forecasting_secret"

@app.before_request
def session_management():

    session.permanent = True

    now = int(time.time())

    # First request
    if 'last_activity' not in session:
        session['last_activity'] = now
        return

    last_activity = session['last_activity']

    # If 30 minutes passed
    if now - last_activity > 600:
        session.clear()
        return redirect(url_for('auth.distributor_login'))

    # Update time
    session['last_activity'] = now
# -----------------------------
# Landing Page Route (IMPORTANT)
# -----------------------------
@app.route("/")
def landing_page():
    return render_template("landing.html")


# -----------------------------
# Register Blueprints
# -----------------------------
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(admin_bp, url_prefix='/admin')
app.register_blueprint(distributor_bp, url_prefix='/distributor')
# -----------------------------
# Run Server
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True)