"""Public profiles and native Sound Lab music collections."""

import re

from flask import Blueprint, abort, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError

from forum.models import CollectionItem, Post, Profile, Reaction, User, db
from forum.musicbrainz import MusicBrainzUnavailable, search_releases


profiles_bp = Blueprint("profiles", __name__)
AVATAR_STYLES = {"synth", "guitar", "bass", "drums", "vocalist", "dj", "horns", "lyricist"}
MBID_PATTERN = re.compile(r"^[0-9a-fA-F-]{36}$")


def _profile_for(user, create=False):
    if user.profile_record is None:
        if not create:
            return Profile(avatar_style="synth")
        user.profile_record = Profile(avatar_style="synth")
        db.session.flush()
    return user.profile_record


@profiles_bp.route("/users/<username>")
def profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    active_tab = request.args.get("tab", "collection")
    if active_tab not in {"collection", "reactions"}:
        active_tab = "collection"

    reactions_query = (
        Reaction.query
        .join(Post, Reaction.post_id == Post.id)
        .filter(Reaction.user_id == user.id)
        .order_by(Reaction.id.desc())
    )
    if not current_user.is_authenticated:
        reactions_query = reactions_query.filter(Post.visibility == "public")

    grouped_reactions = {"like": [], "heart": [], "dislike": []}
    for reaction in reactions_query.all():
        if reaction.reaction_type in grouped_reactions:
            grouped_reactions[reaction.reaction_type].append(reaction)

    return render_template(
        "profile.html",
        profile_user=user,
        profile=_profile_for(user),
        active_tab=active_tab,
        grouped_reactions=grouped_reactions,
        reaction_total=sum(len(items) for items in grouped_reactions.values()),
    )


@profiles_bp.route("/profile/edit", methods=["GET", "POST"])
@login_required
def edit_profile():
    profile = _profile_for(current_user, create=True)
    if request.method == "POST":
        avatar_style = request.form.get("avatar_style", "synth")
        bio = request.form.get("bio", "").strip()
        if avatar_style not in AVATAR_STYLES or len(bio) > 1000:
            return render_template(
                "edit_profile.html",
                profile=profile,
                errors=["Choose a valid avatar and keep your bio under 1,000 characters."],
            ), 400
        profile.display_name = request.form.get("display_name", "").strip()[:80]
        profile.location = request.form.get("location", "").strip()[:100]
        profile.instruments = request.form.get("instruments", "").strip()[:255]
        profile.favorite_genres = request.form.get("favorite_genres", "").strip()[:255]
        profile.avatar_style = avatar_style
        profile.bio = bio
        db.session.commit()
        return redirect(url_for("profiles.profile", username=current_user.username))
    return render_template("edit_profile.html", profile=profile)


@profiles_bp.route("/collection/search")
@login_required
def collection_search():
    query = request.args.get("q", "").strip()
    try:
        page = max(1, int(request.args.get("page", 1)))
    except ValueError:
        page = 1
    results = []
    error = None
    if query:
        try:
            results = search_releases(query, offset=(page - 1) * 24)
        except MusicBrainzUnavailable as exc:
            error = str(exc)
    return render_template(
        "collection_search.html",
        query=query,
        results=results,
        search_error=error,
        page=page,
        has_next=len(results) == 24,
    )


@profiles_bp.route("/collection/add", methods=["POST"])
@login_required
def add_collection_item():
    release_id = request.form.get("release_id", "").strip()
    if not MBID_PATTERN.fullmatch(release_id):
        abort(400)
    item = CollectionItem(
        user_id=current_user.id,
        musicbrainz_id=release_id,
        artist_name=request.form.get("artist", "Unknown artist").strip()[:255] or "Unknown artist",
        release_title=request.form.get("title", "Untitled release").strip()[:255] or "Untitled release",
        release_date=request.form.get("date", "").strip()[:20],
        release_format=request.form.get("format", "").strip()[:80],
        cover_url=f"https://coverartarchive.org/release-group/{release_id}/front-500",
    )
    db.session.add(item)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
    return redirect(url_for("profiles.profile", username=current_user.username))


@profiles_bp.route("/collection/<int:item_id>/remove", methods=["POST"])
@login_required
def remove_collection_item(item_id):
    item = CollectionItem.query.filter_by(id=item_id, user_id=current_user.id).first_or_404()
    db.session.delete(item)
    db.session.commit()
    return redirect(url_for("profiles.profile", username=current_user.username))
