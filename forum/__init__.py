from flask import Flask

from forum.auth import auth_bp
from forum.routes import rt


def create_app():
    """Create and configure the Flask application."""

    # Create the main Flask application.
    app = Flask(__name__, instance_relative_config=False)

    # Load settings from the Config class.
    app.config.from_object("config.Config")

    # Connect each group of routes to the application.
    app.register_blueprint(rt)
    app.register_blueprint(auth_bp)

    # Connect the database to the application.
    from forum.models import db

    db.init_app(app)

    # Create any database tables that do not exist yet.
    with app.app_context():
        db.create_all()

    # Return the finished Flask application.
    return app