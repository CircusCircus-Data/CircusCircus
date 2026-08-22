import datetime

from flask import Blueprint, abort, render_template, request, redirect, url_for
from flask_login import current_user, login_required

from forum.models import Post, Comment, db, error, valid_comment


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

    content = request.form.get("content", "").strip()
    if not valid_comment(content):
        return error("Comment must be between 1 and 5000 characters long!"), 400

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


def _can_manage_comment(comment):
    """Allow a comment author or an administrator to manage a comment."""

    return current_user.id == comment.user_id or current_user.admin


@comments_bp.route("/comments/<int:comment_id>/edit", methods=["GET", "POST"])
@login_required
def edit_comment(comment_id):
    """Display or process the form for editing a comment."""

    comment = db.get_or_404(Comment, comment_id)
    if not _can_manage_comment(comment):
        abort(403)

    if request.method == "GET":
        return render_template("editcomment.html", comment=comment)

    content = request.form.get("content", "").strip()
    if not valid_comment(content):
        return render_template(
            "editcomment.html",
            comment=comment,
            errors=["Comment must be between 1 and 5000 characters long!"],
            submitted_content=content,
        ), 400

    comment.content = content
    db.session.commit()
    return redirect(url_for("posts.viewpost", post=comment.post_id))


@comments_bp.route("/comments/<int:comment_id>/delete", methods=["POST"])
@login_required
def delete_comment(comment_id):
    """Delete a comment owned by the user or managed by an administrator."""

    comment = db.get_or_404(Comment, comment_id)
    if not _can_manage_comment(comment):
        abort(403)

    post_id = comment.post_id
    db.session.delete(comment)
    db.session.commit()
    return redirect(url_for("posts.viewpost", post=post_id))
