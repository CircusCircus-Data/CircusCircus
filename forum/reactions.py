from flask import Blueprint, request, redirect
from flask_login import current_user, login_required

from forum.models import Post, Reaction, db, error


# This Blueprint groups all reaction-related routes together.
reactions_bp = Blueprint("reactions", __name__)


# These are the only reaction types the application accepts.
VALID_REACTIONS = {"like", "dislike", "heart"}


# Add, change, or remove a reaction from a post.
@reactions_bp.route("/action_reaction", methods=["POST"])
@login_required
def action_reaction():
    # Read the post and reaction information from the form.
    post_id = request.form.get("post_id", type=int)
    reaction_type = request.form.get("reaction_type", "").lower()

    # Reject anything other than like, dislike, or heart.
    if reaction_type not in VALID_REACTIONS:
        return error("That reaction type is not allowed!")

    # Search for the post receiving the reaction.
    selected_post = db.session.get(Post, post_id)

    if not selected_post:
        return error("That post does not exist!")

    # Check whether this user already reacted to this post.
    existing_reaction = Reaction.query.filter_by(
        user_id=current_user.id,
        post_id=post_id,
    ).first()

    if existing_reaction:
        if existing_reaction.reaction_type == reaction_type:
            # Clicking the same reaction again removes it.
            db.session.delete(existing_reaction)
        else:
            # Clicking a different reaction changes it.
            existing_reaction.reaction_type = reaction_type
    else:
        # Create the user's first reaction to this post.
        new_reaction = Reaction(reaction_type)

        # Connect the reaction to the user and post
        # before trying to save it.
        new_reaction.user_id = current_user.id
        new_reaction.post_id = selected_post.id

        # Add the completed reaction to the database session.
        db.session.add(new_reaction)

    # Save the change in MySQL.
    db.session.commit()

    # Return the user to the same post.
    return redirect("/viewpost?post=" + str(post_id))