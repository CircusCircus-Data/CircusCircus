import datetime

from flask import Blueprint, abort, render_template, request, redirect, url_for
from flask_login import current_user, login_required

from forum.models import (
    Post,
    Comment,
    Reaction,
    Subforum,
    valid_content,
    valid_title,
    db,
    generateLinkPath,
    error,
)
from forum.media import valid_image_url, valid_video_url, video_embed_url


# This Blueprint groups all post-related routes together.
posts_bp = Blueprint("posts", __name__)


# Display a subforum and its posts.
@posts_bp.route("/subforum")
def subforum():
    subforum_id = int(request.args.get("sub"))

    # Search for the selected subforum.
    selected_subforum = Subforum.query.filter(
        Subforum.id == subforum_id
    ).first()

    if not selected_subforum:
        return error("That subforum does not exist!")

    # Logged-out visitors may only discover public posts. Authenticated users
    # may also see private posts, as defined by the forum's visibility policy.
    posts_query = Post.query.filter(Post.subforum_id == subforum_id)
    if not current_user.is_authenticated:
        posts_query = posts_query.filter(Post.visibility == "public")

    posts = posts_query.order_by(Post.id.desc()).limit(50)

    # Create the navigation path shown above the posts.
    subforum_path = generateLinkPath(selected_subforum.id)

    # Find any smaller subforums inside this subforum.
    child_subforums = Subforum.query.filter(
        Subforum.parent_id == subforum_id
    ).all()

    return render_template(
        "subforum.html",
        subforum=selected_subforum,
        posts=posts,
        subforums=child_subforums,
        path=subforum_path,
        reaction_counts={},
        current_reaction=None,
    )


# Display the form used to create a post.
@posts_bp.route("/addpost")
@login_required
def addpost():
    subforum_id = int(request.args.get("sub"))

    selected_subforum = Subforum.query.filter(
        Subforum.id == subforum_id
    ).first()

    if not selected_subforum:
        return error("That subforum does not exist!")

    return render_template(
        "createpost.html",
        subforum=selected_subforum,
    )


# Display one post and all of its comments.
@posts_bp.route("/viewpost")
def viewpost():
    post_id = int(request.args.get("post"))

    selected_post = Post.query.filter(Post.id == post_id).first()

    if not selected_post:
        return error("That post does not exist!")

    # Return 404 so logged-out visitors cannot use direct URLs to discover
    # whether a private post exists.
    if (
        selected_post.visibility == "private"
        and not current_user.is_authenticated
    ):
        abort(404)

    subforum_path = generateLinkPath(selected_post.subforum.id)

    comments = (
        Comment.query
        .filter(Comment.post_id == post_id)
        .order_by(Comment.id.desc())
    )

    # Begin each reaction total at zero.
    reaction_counts = {
        "like": 0,
        "dislike": 0,
        "heart": 0,
    }

    # Count each reaction attached to this post.
    for reaction in selected_post.reactions:
        if reaction.reaction_type in reaction_counts:
            reaction_counts[reaction.reaction_type] += 1

    # Start with no selected reaction.
    current_reaction = None

    # Find the logged-in user's reaction, if one exists.
    if current_user.is_authenticated:
        user_reaction = Reaction.query.filter_by(
            user_id=current_user.id,
            post_id=post_id,
        ).first()

        if user_reaction:
            current_reaction = user_reaction.reaction_type

    return render_template(
        "viewpost.html",
        post=selected_post,
        path=subforum_path,
        comments=comments,
        reaction_counts=reaction_counts,
        current_reaction=current_reaction,
        video_embed_url=video_embed_url(selected_post.video_url),
    )


# Process the form used to create a new post.
@posts_bp.route("/action_post", methods=["POST"])
@login_required
def action_post():
    subforum_id = int(request.args.get("sub"))

    selected_subforum = Subforum.query.filter(
        Subforum.id == subforum_id
    ).first()

    if not selected_subforum:
        return redirect("/")

    title = request.form["title"]
    content = request.form["content"]
    visibility = request.form.get("visibility", "public")
    image_url = request.form.get("image_url", "").strip()
    video_url = request.form.get("video_url", "").strip()

    # Store any validation errors inside this list.
    errors = []

    if not valid_title(title):
        errors.append(
            "Title must be between 4 and 140 characters long!"
        )

    if not valid_content(content):
        errors.append(
            "Post must be between 10 and 5000 characters long!"
        )

    if visibility not in {"public", "private"}:
        errors.append("Post visibility must be Public or Private!")

    if not valid_image_url(image_url):
        errors.append(
            "Image must be an HTTPS link ending in JPG, JPEG, PNG, GIF, or WEBP."
        )

    if not valid_video_url(video_url):
        errors.append("Video must be a valid HTTPS YouTube or Vimeo link.")

    # Redisplay the form if any information is invalid.
    if errors:
        return render_template(
            "createpost.html",
            subforum=selected_subforum,
            errors=errors,
            selected_visibility=visibility,
            submitted_title=title,
            submitted_content=content,
            submitted_image_url=image_url,
            submitted_video_url=video_url,
        )

    # Create and connect the new post.
    new_post = Post(
        title,
        content,
        datetime.datetime.now(),
        visibility,
        image_url or None,
        video_url or None,
    )

    selected_subforum.posts.append(new_post)
    current_user.posts.append(new_post)

    db.session.commit()

    return redirect("/viewpost?post=" + str(new_post.id))


def _can_manage_post(post):
    """Allow a post author or an administrator to manage a post."""

    return current_user.id == post.user_id or current_user.admin


@posts_bp.route("/posts/<int:post_id>/edit", methods=["GET", "POST"])
@login_required
def edit_post(post_id):
    """Display or process the form for editing an existing post."""

    post = db.get_or_404(Post, post_id)
    if not _can_manage_post(post):
        abort(403)

    if request.method == "GET":
        return render_template("editpost.html", post=post)

    title = request.form.get("title", "").strip()
    content = request.form.get("content", "").strip()
    visibility = request.form.get("visibility", "public")
    image_url = request.form.get("image_url", "").strip()
    video_url = request.form.get("video_url", "").strip()
    errors = []

    if not valid_title(title):
        errors.append("Title must be between 5 and 139 characters long!")
    if not valid_content(content):
        errors.append("Post must be between 11 and 4999 characters long!")
    if visibility not in {"public", "private"}:
        errors.append("Post visibility must be Public or Private!")
    if not valid_image_url(image_url):
        errors.append(
            "Image must be an HTTPS link ending in JPG, JPEG, PNG, GIF, or WEBP."
        )
    if not valid_video_url(video_url):
        errors.append("Video must be a valid HTTPS YouTube or Vimeo link.")

    if errors:
        return render_template(
            "editpost.html",
            post=post,
            errors=errors,
            submitted_title=title,
            submitted_content=content,
            selected_visibility=visibility,
            submitted_image_url=image_url,
            submitted_video_url=video_url,
        ), 400

    post.title = title
    post.content = content
    post.visibility = visibility
    post.image_url = image_url or None
    post.video_url = video_url or None
    db.session.commit()
    return redirect(url_for("posts.viewpost", post=post.id))


@posts_bp.route("/posts/<int:post_id>/delete", methods=["POST"])
@login_required
def delete_post(post_id):
    """Delete a post and its attached comments and reactions."""

    post = db.get_or_404(Post, post_id)
    if not _can_manage_post(post):
        abort(403)

    subforum_id = post.subforum_id
    db.session.delete(post)
    db.session.commit()
    return redirect(url_for("posts.subforum", sub=subforum_id))
