# cyberjackal_mkv/trader_app/routes/main_routes.py
# No changes are needed for this file, but it is part of the package structure.
# Its only job is to serve the main HTML page of the dashboard.

from flask import Blueprint, render_template

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Serves the main Orion UI dashboard (index.html)."""
    return render_template('index.html')
