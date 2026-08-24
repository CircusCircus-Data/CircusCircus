"""Public profiles and native Sound Lab music collections."""

import datetime
import re

from flask import Blueprint, abort, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError

from forum.models import CollectionItem, Post, Profile, Reaction, User, db
from forum.musicbrainz import MusicBrainzUnavailable, search_releases


profiles_bp = Blueprint("profiles", __name__)
STARTER_AVATARS = (
    ("starter-vocalist", "Vintage vocalist"),
    ("starter-turntablist", "Turntable DJ"),
    ("starter-controller", "Controller player"),
    ("starter-beatmaker", "Beat maker"),
)
COLOR_AVATAR_TIERS = (
    (10, (
    ("guitar", "Punk guitarist"), ("drums", "Drummer"),
    ("bass", "Bass player"), ("synth", "Synth player"),
    ("vocalist", "Vocalist"), ("dj", "DJ"),
    ("horns", "Horn player"), ("lyricist", "Lyricist"),
    )),
    (25, (
    ("guitar-alt", "Punk guitarist II"), ("drums-alt", "Drummer II"),
    ("bass-alt", "Bass player II"), ("synth-alt", "Synth player II"),
    ("vocalist-alt", "Vocalist II"), ("dj-alt", "DJ II"),
    ("horns-alt", "Horn player II"), ("lyricist-alt", "Lyricist II"),
    )),
)
HEADLINER_AVATARS = {
    "premium-synth": ("Synth engineer", 50),
    "premium-vocalist": ("Spotlight vocalist", 100),
    "premium-producer": ("Beat producer", 200),
    "premium-percussion": ("Percussionist", 400),
}
DEFAULT_AVATAR_STYLE = "starter-controller"
AVATAR_THRESHOLDS = {
    style: 0 for style, _label in STARTER_AVATARS
}
for threshold, avatars in COLOR_AVATAR_TIERS:
    AVATAR_THRESHOLDS.update({style: threshold for style, _label in avatars})
AVATAR_THRESHOLDS.update({
    style: threshold
    for style, (_label, threshold) in HEADLINER_AVATARS.items()
})
AVATAR_STYLES = set(AVATAR_THRESHOLDS)
QUALIFYING_POST_MIN_CHARACTERS = 100
QUALIFYING_POST_MIN_AGE = datetime.timedelta(hours=24)
MBID_PATTERN = re.compile(r"^[0-9a-fA-F-]{36}$")


def qualifying_post_count(user, now=None):
    """Count public, substantial, mature, non-duplicate discussion posts."""

    cutoff = (now or datetime.datetime.now()) - QUALIFYING_POST_MIN_AGE
    posts = (
        Post.query
        .filter(
            Post.user_id == user.id,
            Post.visibility == "public",
            Post.postdate <= cutoff,
        )
        .order_by(Post.postdate.asc(), Post.id.asc())
        .all()
    )
    seen_content = set()
    count = 0
    for post in posts:
        content = post.content or ""
        if len(re.sub(r"\s+", "", content)) < QUALIFYING_POST_MIN_CHARACTERS:
            continue
        normalized_content = " ".join(content.casefold().split())
        if normalized_content in seen_content:
            continue
        seen_content.add(normalized_content)
        count += 1
    return count


def _avatar_choices(post_count):
    starters = [
        {"style": style, "label": label, "threshold": 0, "unlocked": True}
        for style, label in STARTER_AVATARS
    ]
    color_tiers = [
        {
            "threshold": threshold,
            "avatars": [
                {
                    "style": style,
                    "label": label,
                    "threshold": threshold,
                    "unlocked": post_count >= threshold,
                }
                for style, label in avatars
            ],
        }
        for threshold, avatars in COLOR_AVATAR_TIERS
    ]
    headliners = [
        {
            "style": style,
            "label": label,
            "threshold": threshold,
            "unlocked": post_count >= threshold,
        }
        for style, (label, threshold) in HEADLINER_AVATARS.items()
    ]
    return starters, color_tiers, headliners


def _can_use_avatar(style, post_count):
    return style in AVATAR_THRESHOLDS and post_count >= AVATAR_THRESHOLDS[style]


def _profile_for(user, create=False):
    if user.profile_record is None:
        if not create:
            return Profile(avatar_style=DEFAULT_AVATAR_STYLE)
        user.profile_record = Profile(avatar_style=DEFAULT_AVATAR_STYLE)
        db.session.flush()
    return user.profile_record


def displayed_avatar_style(user, post_count=None):
    """Return only an avatar the user has currently earned."""

    profile = _profile_for(user)
    count = qualifying_post_count(user) if post_count is None else post_count
    return profile.avatar_style if _can_use_avatar(profile.avatar_style, count) else DEFAULT_AVATAR_STYLE


profiles_bp.add_app_template_global(displayed_avatar_style)


@profiles_bp.route("/users/<username>")
def profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    profile_record = _profile_for(user)
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

    post_count = qualifying_post_count(user)
    avatar_style = displayed_avatar_style(user, post_count=post_count)
    return render_template(
        "profile.html",
        profile_user=user,
        profile=profile_record,
        avatar_style=avatar_style,
        active_tab=active_tab,
        grouped_reactions=grouped_reactions,
        reaction_total=sum(len(items) for items in grouped_reactions.values()),
    )


@profiles_bp.route("/profile/edit", methods=["GET", "POST"])
@login_required
def edit_profile():
    profile = _profile_for(current_user, create=True)
    post_count = qualifying_post_count(current_user)
    starter_avatars, color_avatar_tiers, headliner_avatars = _avatar_choices(post_count)
    if request.method == "POST":
        avatar_style = request.form.get("avatar_style", DEFAULT_AVATAR_STYLE)
        bio = request.form.get("bio", "").strip()
        if not _can_use_avatar(avatar_style, post_count) or len(bio) > 1000:
            if avatar_style in AVATAR_THRESHOLDS:
                required = AVATAR_THRESHOLDS[avatar_style]
                error = f"That avatar requires {required} qualifying posts."
            else:
                error = "Choose a valid avatar and keep your bio under 1,000 characters."
            return render_template(
                "edit_profile.html",
                profile=profile,
                errors=[error],
                qualifying_post_count=post_count,
                starter_avatars=starter_avatars,
                color_avatar_tiers=color_avatar_tiers,
                headliner_avatars=headliner_avatars,
            ), 400
        profile.display_name = request.form.get("display_name", "").strip()[:80]
        profile.location = request.form.get("location", "").strip()[:100]
        profile.instruments = request.form.get("instruments", "").strip()[:255]
        profile.favorite_genres = request.form.get("favorite_genres", "").strip()[:255]
        profile.avatar_style = avatar_style
        profile.bio = bio
        db.session.commit()
        return redirect(url_for("profiles.profile", username=current_user.username))
    return render_template(
        "edit_profile.html",
        profile=profile,
        qualifying_post_count=post_count,
        starter_avatars=starter_avatars,
        color_avatar_tiers=color_avatar_tiers,
        headliner_avatars=headliner_avatars,
    )


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
