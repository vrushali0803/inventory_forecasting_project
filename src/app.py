from flask import Flask, render_template, session, redirect, url_for
import os
import time
from dotenv import load_dotenv

# Load env variables
load_dotenv()

# Import Blueprints
from routes.admin_routes import admin_bp
from routes.distributor_routes import distributor_bp
from routes.auth_routes import auth_bp

def create_app():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    static_path = os.path.join(base_dir, "static")

    app = Flask(__name__, static_folder=static_path)

    app.secret_key = os.getenv("SECRET_KEY")

    # -----------------------------
    # SESSION MANAGEMENT
    # -----------------------------
    @app.before_request
    def session_management():
        session.permanent = True
        now = int(time.time())

        if 'last_activity' not in session:
            session['last_activity'] = now
            return

        if now - session['last_activity'] > 1800:
            session.clear()
            return redirect(url_for('auth.distributor_login'))

        session['last_activity'] = now

    # -----------------------------
    # ROUTES
    # -----------------------------
    @app.route("/")
    def landing_page():
        return render_template("landing.html")

    # -----------------------------
    # REGISTER BLUEPRINTS
    # -----------------------------
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(distributor_bp, url_prefix='/distributor')

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)