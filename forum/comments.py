import datetime

from flask import Blueprint, request, redirect
from flask_login import current_user, login_required

from forum.models import Post, Comment, db, error


# This Blueprint groups all comment-related routes together.
comments_bp = Blueprint("comments", __name__)


# Add a comment to an existing post.
@comments_bp.route("/action_comment", methods=["POST"])
@login_required
def add_comment():
    post_id = int(request.args.get("post"))

    # Search for the post receiving the comment.
    selected_post = Post.query.filter(Post.id == post_id).first()

    if not selected_post:
        return error("That post does not exist!")

    content = request.form["content"]

    # Create a new comment with the current date and time.
    new_comment = Comment(
        content,
        datetime.datetime.now(),
    )

    # Connect the comment to the logged-in user.
    current_user.comments.append(new_comment)

    # Connect the comment to the selected post.
    selected_post.comments.append(new_comment)

    # Save the comment in the database.
    db.session.commit()

    return redirect("/viewpost?post=" + str(post_id))