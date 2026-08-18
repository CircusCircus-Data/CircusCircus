"""
Flask configuration variables.
"""

from os import environ, path

from dotenv import load_dotenv
from sqlalchemy.engine import URL


# Find the main CircusCircus project folder.
basedir = path.abspath(path.dirname(__file__))

# Load private settings from the .env file.
load_dotenv(path.join(basedir, ".env"))


class Config:
    """Store the settings used by the Flask application."""

    # General Flask settings
    SECRET_KEY = "kristofer"
    FLASK_APP = "forum.app"

    # Build the MySQL connection without exposing the password.
    SQLALCHEMY_DATABASE_URI = URL.create(
        drivername="mysql+pymysql",
        username=environ.get("DATABASE_USER"),
        password=environ.get("DATABASE_PASSWORD"),
        host=environ.get("DATABASE_HOST", "localhost"),
        database=environ.get("DATABASE_NAME"),
    )

    # Additional database settings
    SQLALCHEMY_ECHO = False
    SQLALCHEMY_TRACK_MODIFICATIONS = False