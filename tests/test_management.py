"""Tests for post, comment, and account management."""

import datetime
import unittest

from flask import Flask
from flask_login import LoginManager

from forum.comments import comments_bp
from forum.formatting import render_markdown
from forum.messages import Message
from forum.models import Comment, Post, Reaction, Subforum, User, db
from forum.posts import posts_bp
from forum.settings import settings_bp


class ManagementTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(
            __name__,
            template_folder="../forum/templates",
            static_folder="../forum/static",
        )
        self.app.config.update(
            SECRET_KEY="management-test",
            SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
            SQLALCHEMY_TRACK_MODIFICATIONS=False,
            SITE_NAME="Test Forum",
        )
        db.init_app(self.app)
        self.app.register_blueprint(posts_bp)
        self.app.register_blueprint(comments_bp)
        self.app.register_blueprint(settings_bp)
        self.app.add_template_filter(render_markdown, "markdown")

        @self.app.route("/")
        def index():
            return "home"

        login_manager = LoginManager(self.app)

        @login_manager.user_loader
        def load_user(user_id):
            return db.session.get(User, int(user_id))

        with self.app.app_context():
            db.create_all()
            author = User("author@example.com", "author", "secret1")
            other = User("other@example.com", "otheruser", "secret2")
            admin = User("admin@example.com", "admin", "secret3")
            admin.admin = True
            subforum = Subforum("General", "General discussion")
            post = Post(
                "Original post",
                "Original post content",
                datetime.datetime.now(),
            )
            author.posts.append(post)
            subforum.posts.append(post)
            comment = Comment("Original comment", datetime.datetime.now())
            other.comments.append(comment)
            post.comments.append(comment)
            reaction = Reaction("like")
            other.reactions.append(reaction)
            post.reactions.append(reaction)
            db.session.add_all([author, other, admin, subforum])
            db.session.commit()

            self.author_id = author.id
            self.other_id = other.id
            self.admin_id = admin.id
            self.post_id = post.id
            self.comment_id = comment.id

        self.client = self.app.test_client()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def log_in(self, user_id):
        with self.client.session_transaction() as session:
            session["_user_id"] = str(user_id)
            session["_fresh"] = True

    def test_author_can_edit_post(self):
        self.log_in(self.author_id)
        response = self.client.post(
            f"/posts/{self.post_id}/edit",
            data={
                "title": "Updated post",
                "content": "Updated post content",
                "visibility": "private",
            },
        )
        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            post = db.session.get(Post, self.post_id)
            self.assertEqual(post.title, "Updated post")
            self.assertEqual(post.visibility, "private")

    def test_other_user_cannot_edit_or_delete_post(self):
        self.log_in(self.other_id)
        edit_response = self.client.post(
            f"/posts/{self.post_id}/edit",
            data={
                "title": "Stolen post",
                "content": "Someone else's changed content",
                "visibility": "public",
            },
        )
        delete_response = self.client.post(f"/posts/{self.post_id}/delete")
        self.assertEqual(edit_response.status_code, 403)
        self.assertEqual(delete_response.status_code, 403)

    def test_post_delete_cascades_to_comments_and_reactions(self):
        self.log_in(self.author_id)
        response = self.client.post(f"/posts/{self.post_id}/delete")
        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            self.assertIsNone(db.session.get(Post, self.post_id))
            self.assertIsNone(db.session.get(Comment, self.comment_id))
            self.assertEqual(Reaction.query.count(), 0)

    def test_comment_author_can_edit_and_admin_can_delete(self):
        self.log_in(self.other_id)
        response = self.client.post(
            f"/comments/{self.comment_id}/edit",
            data={"content": "Updated comment"},
        )
        self.assertEqual(response.status_code, 302)

        self.log_in(self.admin_id)
        response = self.client.post(f"/comments/{self.comment_id}/delete")
        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            self.assertIsNone(db.session.get(Comment, self.comment_id))

    def test_password_change_requires_current_password(self):
        self.log_in(self.author_id)
        rejected = self.client.post(
            "/settings/password",
            data={
                "current_password": "wrong",
                "new_password": "newpass1",
                "confirm_password": "newpass1",
            },
        )
        self.assertEqual(rejected.status_code, 400)

        accepted = self.client.post(
            "/settings/password",
            data={
                "current_password": "secret1",
                "new_password": "newpass1",
                "confirm_password": "newpass1",
            },
        )
        self.assertEqual(accepted.status_code, 200)
        with self.app.app_context():
            self.assertTrue(db.session.get(User, self.author_id).check_password("newpass1"))

    def test_account_deletion_removes_forum_content(self):
        self.log_in(self.author_id)
        response = self.client.post(
            "/settings/delete",
            data={
                "delete_password": "secret1",
                "delete_confirmation": "DELETE",
            },
        )
        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            self.assertIsNone(db.session.get(User, self.author_id))
            self.assertIsNone(db.session.get(Post, self.post_id))
            self.assertIsNone(db.session.get(Comment, self.comment_id))

    def test_message_history_blocks_account_deletion(self):
        with self.app.app_context():
            author = db.session.get(User, self.author_id)
            other = db.session.get(User, self.other_id)
            db.session.add(Message("Keep this message", sender=author, recipient=other))
            db.session.commit()

        self.log_in(self.author_id)
        response = self.client.post(
            "/settings/delete",
            data={
                "delete_password": "secret1",
                "delete_confirmation": "DELETE",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn(b"cannot be deleted without changing messages", response.data)
        with self.app.app_context():
            self.assertIsNotNone(db.session.get(User, self.author_id))
            self.assertEqual(Message.query.count(), 1)


if __name__ == "__main__":
    unittest.main()
