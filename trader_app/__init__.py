# cyberjackal_mkv/trader_app/__init__.py
# THIS FILE MAKES THE 'trader_app' FOLDER A PYTHON PACKAGE.
# It contains the "application factory" function, which is a best practice
# for creating Flask applications.

import os
import sys
from flask import Flask
from .models import db

# Add shared models to path for security modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'shared_models'))
from security_middleware import SecurityMiddleware
from security_config import load_security_config

def create_app():
    """Application factory function with enhanced security."""
    app = Flask(__name__)
    
    # Load security configuration
    try:
        security_config = load_security_config()
    except Exception:
        # Fallback if security config fails to load
        security_config = None

    # Configure the database using the URL from the environment variables
    db_url = os.getenv('DATABASE_URL')
    if db_url and db_url.startswith("postgresql://"):
        # This replace() call is a common fix for SQLAlchemy 1.4+ compatibility
        db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Enhanced security configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'fallback-secret-key-change-in-production')
    if security_config:
        app.config['MAX_CONTENT_LENGTH'] = security_config.max_request_size_mb * 1024 * 1024
        app.config['PERMANENT_SESSION_LIFETIME'] = security_config.session_timeout_minutes * 60
    
    # Initialize security middleware
    try:
        security_middleware = SecurityMiddleware()
        security_middleware.init_app(app)
    except Exception as e:
        print(f"Warning: Could not initialize security middleware: {e}")

    # Initialize extensions with the app
    db.init_app(app)

    # Import and register the blueprints for our routes
    # This keeps our routes organized in separate files.
    from .routes import main_routes, api_routes
    app.register_blueprint(main_routes.main_bp)
    app.register_blueprint(api_routes.api_bp, url_prefix='/api')
    
    # Register security routes for admin access
    try:
        from .routes.security_routes import security_bp
        app.register_blueprint(security_bp, url_prefix='/admin')
    except Exception as e:
        print(f"Warning: Could not register security routes: {e}")

    return app
