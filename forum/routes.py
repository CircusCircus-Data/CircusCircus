import datetime

from flask import Blueprint, request, redirect
from flask_login import current_user, login_required

from forum.models import Post, Comment, db, error


# This Blueprint temporarily contains the comment route.
rt = Blueprint("routes", __name__)


# Add a comment to an existing post.
@rt.route("/action_comment", methods=["POST", "GET"])
@login_required
def comment():
    post_id = int(request.args.get("post"))

    # Search for the post receiving the comment.
    selected_post = Post.query.filter(Post.id == post_id).first()

    if not selected_post:
        return error("That post does not exist!")

    content = request.form["content"]

    # Create the new comment.
    new_comment = Comment(
        content,
        datetime.datetime.now(),
    )

    # Connect the comment to its user and post.
    current_user.comments.append(new_comment)
    selected_post.comments.append(new_comment)

    db.session.commit()

    return redirect("/viewpost?post=" + str(post_id))