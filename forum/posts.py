import datetime

from flask import Blueprint, render_template, request, redirect
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

    # Get the 50 newest posts from this subforum.
    posts = (
        Post.query
        .filter(Post.subforum_id == subforum_id)
        .order_by(Post.id.desc())
        .limit(50)
    )

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

    # Redisplay the form if any information is invalid.
    if errors:
        return render_template(
            "createpost.html",
            subforum=selected_subforum,
            errors=errors,
        )

    # Create and connect the new post.
    new_post = Post(
        title,
        content,
        datetime.datetime.now(),
    )

    selected_subforum.posts.append(new_post)
    current_user.posts.append(new_post)

    db.session.commit()

    return redirect("/viewpost?post=" + str(new_post.id))