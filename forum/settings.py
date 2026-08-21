from flask import Blueprint, render_template, request
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError

from forum.models import User, db
from forum.user import valid_email, valid_username


# Group account-settings routes in their own Blueprint.
settings_bp = Blueprint("settings", __name__)


# Only authenticated users may view their account settings.
@settings_bp.route("/settings")
@login_required
def view_settings():
    return render_template("settings.html")


# Validate settings submitted by the authenticated user.
@settings_bp.route("/action_settings", methods=["POST"])
@login_required
def action_settings():
    username = request.form.get("username", "").strip()
    email = request.form.get("email", "").strip()
    errors = []

    if not valid_username(username):
        errors.append("Username must be 4 to 40 valid characters.")
    elif User.query.filter(
        User.username == username,
        User.id != current_user.id,
    ).first():
        errors.append("Username is already taken!")

    if not valid_email(email):
        errors.append("Enter a valid email address.")
    elif User.query.filter(
        User.email == email,
        User.id != current_user.id,
    ).first():
        errors.append("An account already exists with this email!")

    if errors:
        return render_template(
            "settings.html",
            errors=errors,
            submitted_username=username,
            submitted_email=email,
        )

    # Update only the authenticated user's approved account fields.
    current_user.username = username
    current_user.email = email

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return render_template(
            "settings.html",
            errors=["That username or email is already in use."],
            submitted_username=username,
            submitted_email=email,
        )

    return render_template(
        "settings.html",
        success_message="Your account settings were saved.",
    )
