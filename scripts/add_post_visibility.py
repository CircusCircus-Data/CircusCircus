"""Add post visibility to an existing CircusCircus database."""

from sqlalchemy import inspect, text


def add_post_visibility_column(engine):
    """Add the visibility column once and preserve old posts as public."""

    columns = {column["name"] for column in inspect(engine).get_columns("post")}
    if "visibility" in columns:
        return False

    with engine.begin() as connection:
        connection.execute(
            text(
                "ALTER TABLE post ADD COLUMN visibility "
                "VARCHAR(10) NOT NULL DEFAULT 'public'"
            )
        )
    return True


if __name__ == "__main__":
    from forum.app import app
    from forum.models import db

    with app.app_context():
        changed = add_post_visibility_column(db.engine)
        print("Post visibility column added." if changed else "Column already exists.")
