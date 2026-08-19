from flask import Blueprint, render_template
from flask_login import login_required


# Group account-settings routes in their own Blueprint.
settings_bp = Blueprint("settings", __name__)


# Only authenticated users may view their account settings.
@settings_bp.route("/settings")
@login_required
def view_settings():
    return render_template("settings.html")
