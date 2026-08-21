"""Add optional media-link columns to an existing CircusCircus database."""

from sqlalchemy import inspect, text


def add_post_media_columns(engine):
    """Add missing media columns without changing existing post data."""

    columns = {column["name"] for column in inspect(engine).get_columns("post")}
    statements = []
    if "image_url" not in columns:
        statements.append("ALTER TABLE post ADD COLUMN image_url VARCHAR(2048)")
    if "video_url" not in columns:
        statements.append("ALTER TABLE post ADD COLUMN video_url VARCHAR(2048)")

    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))
    return len(statements)


if __name__ == "__main__":
    from forum.app import app
    from forum.models import db

    with app.app_context():
        changed = add_post_media_columns(db.engine)
        print(f"Added {changed} post media column(s).")
