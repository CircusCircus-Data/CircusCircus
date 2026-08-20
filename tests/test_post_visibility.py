"""Route-level tests for public and private posts."""

import datetime
import unittest

from flask import Flask
from flask_login import LoginManager

from forum.formatting import render_markdown
from forum.models import Post, Subforum, User, db
from forum.posts import posts_bp


class PostVisibilityTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(
            __name__,
            template_folder="../forum/templates",
            static_folder="../forum/static",
        )
        self.app.config.update(
            SECRET_KEY="visibility-test",
            SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
            SQLALCHEMY_TRACK_MODIFICATIONS=False,
            SITE_NAME="Test Forum",
            SITE_DESCRIPTION="",
        )
        db.init_app(self.app)
        self.app.register_blueprint(posts_bp)
        self.app.add_template_filter(render_markdown, "markdown")

        login_manager = LoginManager(self.app)

        @login_manager.user_loader
        def load_user(user_id):
            return db.session.get(User, int(user_id))

        with self.app.app_context():
            db.create_all()
            self.user = User("author@example.com", "author", "secret1")
            self.subforum = Subforum("General", "General discussion")
            public_post = Post(
                "Public post",
                "Public post content",
                datetime.datetime.now(),
            )
            private_post = Post(
                "Private post",
                "Private post content",
                datetime.datetime.now(),
                "private",
            )
            self.user.posts.extend([public_post, private_post])
            self.subforum.posts.extend([public_post, private_post])
            db.session.add_all([self.user, self.subforum])
            db.session.commit()
            self.user_id = self.user.id
            self.subforum_id = self.subforum.id
            self.public_post_id = public_post.id
            self.private_post_id = private_post.id

        self.client = self.app.test_client()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def log_in(self):
        with self.client.session_transaction() as session:
            session["_user_id"] = str(self.user_id)
            session["_fresh"] = True

    def test_public_post_url_remains_accessible(self):
        response = self.client.get(f"/viewpost?post={self.public_post_id}")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Public post content", response.data)

    def test_private_post_direct_url_is_hidden_from_visitor(self):
        response = self.client.get(f"/viewpost?post={self.private_post_id}")
        self.assertEqual(response.status_code, 404)
        self.assertNotIn(b"Private post content", response.data)

    def test_private_post_is_hidden_from_public_subforum_listing(self):
        response = self.client.get(f"/subforum?sub={self.subforum_id}")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Public post", response.data)
        self.assertNotIn(b"Private post", response.data)

    def test_authenticated_user_can_view_private_post(self):
        self.log_in()
        response = self.client.get(f"/viewpost?post={self.private_post_id}")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Private post content", response.data)

    def test_selected_visibility_is_saved(self):
        self.log_in()
        response = self.client.post(
            f"/action_post?sub={self.subforum_id}",
            data={
                "title": "Another private post",
                "content": "Enough content for a valid private post.",
                "visibility": "private",
            },
        )
        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            saved_post = Post.query.filter_by(title="Another private post").one()
            self.assertEqual(saved_post.visibility, "private")

    def test_post_visibility_defaults_to_public(self):
        post = Post("Default post", "Default post content", datetime.datetime.now())
        self.assertEqual(post.visibility, "public")


if __name__ == "__main__":
    unittest.main()
