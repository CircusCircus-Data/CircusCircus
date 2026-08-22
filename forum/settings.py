from flask import Blueprint, redirect, render_template, request, url_for
from flask_login import current_user, login_required, logout_user
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from forum.messages import Message
from forum.models import User, db
from forum.user import valid_email, valid_password, valid_username


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


@settings_bp.route("/settings/password", methods=["POST"])
@login_required
def change_password():
    """Change the authenticated user's password after verification."""

    current_password = request.form.get("current_password", "")
    new_password = request.form.get("new_password", "")
    confirm_password = request.form.get("confirm_password", "")
    errors = []

    if not current_user.check_password(current_password):
        errors.append("Your current password is incorrect.")
    if not valid_password(new_password):
        errors.append(
            "New password must be 6 to 40 characters and use only letters, "
            "numbers, or ! @ # % &."
        )
    if new_password != confirm_password:
        errors.append("New password and confirmation do not match.")

    if errors:
        return render_template(
            "settings.html",
            password_errors=errors,
        ), 400

    current_user.set_password(new_password)
    db.session.commit()
    return render_template(
        "settings.html",
        password_success="Your password was changed.",
    )


@settings_bp.route("/settings/delete", methods=["POST"])
@login_required
def delete_account():
    """Delete an account only when doing so cannot alter message history."""

    password = request.form.get("delete_password", "")
    confirmation = request.form.get("delete_confirmation", "").strip()
    errors = []

    if not current_user.check_password(password):
        errors.append("Your password is incorrect.")
    if confirmation != "DELETE":
        errors.append('Type DELETE exactly to confirm account deletion.')

    has_messages = Message.query.filter(
        or_(
            Message.sender_id == current_user.id,
            Message.recipient_id == current_user.id,
        )
    ).first() is not None
    if has_messages:
        errors.append(
            "This account has direct-message history and cannot be deleted "
            "without changing messages."
        )

    if errors:
        return render_template(
            "settings.html",
            deletion_errors=errors,
        ), 400

    user = current_user._get_current_object()
    logout_user()
    db.session.delete(user)
    db.session.commit()
    return redirect(url_for("index"))
