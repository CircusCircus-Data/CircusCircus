from flask import Blueprint, render_template, request, redirect
from flask_login import login_user, logout_user, login_required

from forum.models import User, db
from forum.user import username_taken, email_taken, valid_username


# This Blueprint groups all account-related routes together.
auth_bp = Blueprint("auth", __name__)


# Display the login and account creation page.
@auth_bp.route("/loginform")
def loginform():
    return render_template("login.html")


# Check the username and password submitted by the user.
@auth_bp.route("/action_login", methods=["POST"])
def action_login():
    username = request.form["username"]
    password = request.form["password"]

    # Search the database for the submitted username.
    user = User.query.filter(User.username == username).first()

    # Log the user in when the username and password are correct.
    if user and user.check_password(password):
        login_user(user)
        return redirect("/")

    # Redisplay the page when the login information is incorrect.
    errors = ["Username or password is incorrect!"]
    return render_template("login.html", errors=errors)


# Log out the current user.
@auth_bp.route("/action_logout")
@login_required
def action_logout():
    logout_user()
    return redirect("/")


# Create a new user account.
@auth_bp.route("/action_createaccount", methods=["POST"])
def action_createaccount():
    username = request.form["username"]
    password = request.form["password"]
    email = request.form["email"]

    # Store any validation errors inside this list.
    errors = []

    if username_taken(username):
        errors.append("Username is already taken!")

    if email_taken(email):
        errors.append("An account already exists with this email!")

    if not valid_username(username):
        errors.append("Username is not valid!")

    # If errors were found, redisplay them on the login page.
    if errors:
        return render_template("login.html", errors=errors)

    # Create and save the new user.
    new_user = User(email, username, password)

    # Give administrator permission to the admin account.
    if new_user.username == "admin":
        new_user.admin = True

    db.session.add(new_user)
    db.session.commit()

    # Log in the user immediately after creating the account.
    login_user(new_user)

    return redirect("/")