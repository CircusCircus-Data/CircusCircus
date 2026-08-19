"""Private-message model and routes."""

import datetime

from flask import Blueprint, abort, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import and_, or_

from forum.models import User, db


messages_bp = Blueprint("messages", __name__, url_prefix="/messages")


class Message(db.Model):
    """A private message sent from one user to another."""

    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    sent_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.datetime.utcnow,
    )
    is_read = db.Column(db.Boolean, nullable=False, default=False)

    sender_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False,
        index=True,
    )
    recipient_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False,
        index=True,
    )

    sender = db.relationship(
        "User",
        foreign_keys=[sender_id],
        backref=db.backref("sent_messages", lazy="dynamic"),
    )
    recipient = db.relationship(
        "User",
        foreign_keys=[recipient_id],
        backref=db.backref("received_messages", lazy="dynamic"),
    )

    def __init__(self, content, sender=None, recipient=None):
        self.content = content
        self.sender = sender
        self.recipient = recipient


def _conversation_query(other_user_id):
    """Return messages shared by the current user and one other user."""

    return Message.query.filter(
        or_(
            and_(
                Message.sender_id == current_user.id,
                Message.recipient_id == other_user_id,
            ),
            and_(
                Message.sender_id == other_user_id,
                Message.recipient_id == current_user.id,
            ),
        )
    )


@messages_bp.route("/send", methods=["POST"])
@login_required
def send_message():
    """Send a message as the currently logged-in user."""

    recipient_id = request.form.get("recipient_id", type=int)
    recipient = db.session.get(User, recipient_id) if recipient_id else None
    content = request.form.get("content", "").strip()

    if recipient is None:
        abort(404)
    if recipient.id == current_user.id:
        abort(400, description="You cannot send a message to yourself.")
    if not content or len(content) > 5000:
        messages = _conversation_query(recipient.id).order_by(Message.sent_at).all()
        return render_template(
            "conversation.html",
            other_user=recipient,
            messages=messages,
            errors=["Messages must be between 1 and 5000 characters long."],
        ), 400

    db.session.add(Message(content, sender=current_user, recipient=recipient))
    db.session.commit()
    return redirect(url_for("messages.conversation", user_id=recipient.id))


@messages_bp.route("/")
@login_required
def inbox():
    """Display one inbox entry for each conversation."""

    all_messages = Message.query.filter(
        or_(
            Message.sender_id == current_user.id,
            Message.recipient_id == current_user.id,
        )
    ).order_by(Message.sent_at.desc(), Message.id.desc()).all()

    conversations = []
    seen_user_ids = set()
    for message in all_messages:
        other_user = (
            message.recipient
            if message.sender_id == current_user.id
            else message.sender
        )
        if other_user.id in seen_user_ids:
            continue

        seen_user_ids.add(other_user.id)
        unread_count = Message.query.filter_by(
            sender_id=other_user.id,
            recipient_id=current_user.id,
            is_read=False,
        ).count()
        conversations.append(
            {
                "user": other_user,
                "last_message": message,
                "unread_count": unread_count,
            }
        )

    users = User.query.filter(User.id != current_user.id).order_by(User.username).all()
    return render_template(
        "inbox.html",
        conversations=conversations,
        users=users,
    )


@messages_bp.route("/conversation/<int:user_id>")
@login_required
def conversation(user_id):
    """Display the current user's conversation with another user."""

    if user_id == current_user.id:
        abort(400, description="You cannot message yourself.")

    other_user = db.session.get(User, user_id)
    if other_user is None:
        abort(404)

    messages = _conversation_query(user_id).order_by(
        Message.sent_at,
        Message.id,
    ).all()

    unread_messages = Message.query.filter_by(
        sender_id=user_id,
        recipient_id=current_user.id,
        is_read=False,
    ).all()
    if unread_messages:
        for message in unread_messages:
            message.is_read = True
        db.session.commit()

    return render_template(
        "conversation.html",
        other_user=other_user,
        messages=messages,
    )
