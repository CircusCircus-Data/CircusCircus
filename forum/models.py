
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
import datetime

# create db here so it can be imported (with the models) into the App object.
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

#OBJECT MODELS
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(40), unique=True)
    password_hash = db.Column(db.String(255))
    email = db.Column(db.String(255), unique=True)
    admin = db.Column(db.Boolean, default=False)
    posts = db.relationship(
        "Post",
        backref="user",
        cascade="all, delete-orphan",
    )
    comments = db.relationship(
        "Comment",
        backref="user",
        cascade="all, delete-orphan",
    )
    reactions = db.relationship(
        "Reaction",
        backref="user",
        cascade="all, delete-orphan",
    )
    profile_record = db.relationship(
        "Profile",
        backref="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    collection_items = db.relationship(
        "CollectionItem",
        backref="user",
        cascade="all, delete-orphan",
        order_by="CollectionItem.added_at.desc()",
    )

    def __init__(self, email, username, password):
        self.email = email
        self.username = username
        self.password_hash = generate_password_hash(password)
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def set_password(self, password):
        """Replace the user's password with a securely generated hash."""

        self.password_hash = generate_password_hash(password)
    
class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(140))
    content = db.Column(db.Text)
    image_url = db.Column(db.String(2048))
    video_url = db.Column(db.String(2048))
    visibility = db.Column(
        db.String(10),
        nullable=False,
        default="public",
        server_default="public",
    )
    comments = db.relationship(
        "Comment",
        backref="post",
        cascade="all, delete-orphan",
    )
    reactions = db.relationship(
        "Reaction",
        backref="post",
        cascade="all, delete-orphan",
    )
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    subforum_id = db.Column(db.Integer, db.ForeignKey('subforum.id'))
    postdate = db.Column(db.DateTime)

    __table_args__ = (
        db.CheckConstraint(
            "visibility IN ('public', 'private')",
            name="valid_post_visibility",
        ),
    )

    #cache stuff
    lastcheck = None
    savedresponce = None
    def __init__(
        self,
        title,
        content,
        postdate,
        visibility="public",
        image_url=None,
        video_url=None,
    ):
        self.title = title
        self.content = content
        self.postdate = postdate
        self.visibility = visibility
        self.image_url = image_url
        self.video_url = video_url
    def get_time_string(self):
        #this only needs to be calculated every so often, not for every request
        #this can be a rudamentary chache
        now = datetime.datetime.now()
        if self.lastcheck is None or (now - self.lastcheck).total_seconds() > 30:
            self.lastcheck = now
        else:
            return self.savedresponce

        diff = now - self.postdate

        seconds = diff.total_seconds()
        print(seconds)
        if seconds / (60 * 60 * 24 * 30) > 1:
            self.savedresponce =  " " + str(int(seconds / (60 * 60 * 24 * 30))) + " months ago"
        elif seconds / (60 * 60 * 24) > 1:
            self.savedresponce =  " " + str(int(seconds / (60*  60 * 24))) + " days ago"
        elif seconds / (60 * 60) > 1:
            self.savedresponce = " " + str(int(seconds / (60 * 60))) + " hours ago"
        elif seconds / (60) > 1:
            self.savedresponce = " " + str(int(seconds / 60)) + " minutes ago"
        else:
            self.savedresponce =  "Just a moment ago!"

        return self.savedresponce

class Subforum(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(140), unique=True)
    description = db.Column(db.Text)
    subforums = db.relationship("Subforum")
    parent_id = db.Column(db.Integer, db.ForeignKey('subforum.id'))
    posts = db.relationship("Post", backref="subforum")
    path = None
    hidden = db.Column(db.Boolean, default=False)
    def __init__(self, title, description):
        self.title = title
        self.description = description

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text)
    postdate = db.Column(db.DateTime)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    post_id = db.Column(db.Integer, db.ForeignKey("post.id"))

    lastcheck = None
    savedresponce = None
    def __init__(self, content, postdate):
        self.content = content
        self.postdate = postdate
    def get_time_string(self):
        #this only needs to be calculated every so often, not for every request
        #this can be a rudamentary chache
        now = datetime.datetime.now()
        if self.lastcheck is None or (now - self.lastcheck).total_seconds() > 30:
            self.lastcheck = now
        else:
            return self.savedresponce

        diff = now - self.postdate
        seconds = diff.total_seconds()
        if seconds / (60 * 60 * 24 * 30) > 1:
            self.savedresponce =  " " + str(int(seconds / (60 * 60 * 24 * 30))) + " months ago"
        elif seconds / (60 * 60 * 24) > 1:
            self.savedresponce =  " " + str(int(seconds / (60*  60 * 24))) + " days ago"
        elif seconds / (60 * 60) > 1:
            self.savedresponce = " " + str(int(seconds / (60 * 60))) + " hours ago"
        elif seconds / (60) > 1:
            self.savedresponce = " " + str(int(seconds / 60)) + " minutes ago"
        else:
            self.savedresponce =  "Just a moment ago!"
        return self.savedresponce

class Reaction(db.Model):
    """Store one user's reaction to one post."""

    id = db.Column(db.Integer, primary_key=True)

    # Store like, dislike, or heart.
    reaction_type = db.Column(db.String(10), nullable=False)

    # Connect the reaction to its user and post.
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False,
    )

    # Connect the reaction to its post.
    post_id = db.Column(
        db.Integer,
        db.ForeignKey("post.id"),
        nullable=False,
    )

    # Add rules that protect the reaction data.
    __table_args__ = (
        # One user can have only one reaction on each post.
        db.UniqueConstraint(
            "user_id",
            "post_id",
            name="unique_user_post_reaction",
        ),

        # Only these three reaction types are accepted.
        db.CheckConstraint(
            "reaction_type IN ('like', 'dislike', 'heart')",
            name="valid_reaction_type",
        ),
    )

    def __init__(self, reaction_type):
        self.reaction_type = reaction_type    


class Profile(db.Model):
    """Store the Sound Lab identity shown on a user's public profile."""

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, unique=True)
    display_name = db.Column(db.String(80))
    bio = db.Column(db.Text)
    location = db.Column(db.String(100))
    instruments = db.Column(db.String(255))
    favorite_genres = db.Column(db.String(255))
    avatar_style = db.Column(db.String(20), nullable=False, default="synth")


class CollectionItem(db.Model):
    """Connect a Sound Lab user to an enriched MusicBrainz release."""

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    # Keep the original database column name for compatibility with local
    # tables created during development; values are canonical release-group IDs.
    musicbrainz_id = db.Column("musicbrainz_release_id", db.String(36), nullable=False)
    artist_name = db.Column(db.String(255), nullable=False)
    release_title = db.Column(db.String(255), nullable=False)
    release_date = db.Column(db.String(20))
    release_format = db.Column(db.String(80))
    cover_url = db.Column(db.String(2048))
    personal_note = db.Column(db.String(500))
    favorite = db.Column(db.Boolean, nullable=False, default=False)
    added_at = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint(
            "user_id",
            "musicbrainz_release_id",
            name="unique_user_musicbrainz_release",
        ),
    )

def error(errormessage):
	return "<b style=\"color: red;\">" + errormessage + "</b>"

def generateLinkPath(subforumid):
	links = []
	subforum = Subforum.query.filter(Subforum.id == subforumid).first()
	parent = Subforum.query.filter(Subforum.id == subforum.parent_id).first()
	links.append("<a href=\"/subforum?sub=" + str(subforum.id) + "\">" + subforum.title + "</a>")
	while parent is not None:
		links.append("<a href=\"/subforum?sub=" + str(parent.id) + "\">" + parent.title + "</a>")
		parent = Subforum.query.filter(Subforum.id == parent.parent_id).first()
	links.append("<a href=\"/\">Forum Index</a>")
	link = ""
	for l in reversed(links):
		link = link + " / " + l
	return link


#Post checks
def valid_title(title):
	return len(title) > 4 and len(title) < 140
def valid_content(content):
	return len(content) > 10 and len(content) < 5000


def valid_comment(content):
    """Return whether comment text is suitable for saving."""

    return 1 <= len(content.strip()) <= 5000
