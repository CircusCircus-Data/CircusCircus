import io
import json
import unittest
import datetime
from unittest.mock import patch

from flask import Flask
from flask_login import LoginManager

from forum.formatting import render_markdown
from forum.models import CollectionItem, Post, Profile, Reaction, Subforum, User, db
from forum.musicbrainz import search_releases
from forum.profiles import profiles_bp


class ProfilesTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__, template_folder="../forum/templates", static_folder="../forum/static")
        self.app.config.update(
            SECRET_KEY="test",
            SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
            TESTING=True,
        )
        self.app.add_template_filter(render_markdown, "markdown")
        db.init_app(self.app)
        self.app.register_blueprint(profiles_bp)
        login_manager = LoginManager(self.app)

        @login_manager.user_loader
        def load_user(user_id):
            return db.session.get(User, int(user_id))

        with self.app.app_context():
            db.create_all()
            user = User("artist@example.com", "soundartist", "password")
            other = User("other@example.com", "otherartist", "password")
            db.session.add_all([user, other])
            db.session.commit()
            self.user_id = user.id
            self.other_id = other.id
        self.client = self.app.test_client()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def login(self, user_id=None):
        with self.client.session_transaction() as session:
            session["_user_id"] = str(user_id or self.user_id)
            session["_fresh"] = True

    def test_public_profile_uses_default_avatar_without_database_write(self):
        response = self.client.get("/users/soundartist")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"avatar-synth", response.data)
        with self.app.app_context():
            self.assertEqual(Profile.query.filter_by(user_id=self.user_id).count(), 0)

    def test_owner_can_edit_profile(self):
        self.login()
        response = self.client.post(
            "/profile/edit",
            data={
                "display_name": "Sound Artist",
                "bio": "Producer and selector.",
                "location": "New York",
                "instruments": "Synthesizer",
                "favorite_genres": "House, ambient",
                "avatar_style": "lyricist",
            },
        )
        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            profile = Profile.query.filter_by(user_id=self.user_id).one()
            self.assertEqual(profile.display_name, "Sound Artist")
            self.assertEqual(profile.avatar_style, "lyricist")

    def test_collection_item_is_unique_and_owner_can_remove_it(self):
        self.login()
        release = {
            "release_id": "76df3287-6cda-33eb-8e9a-044b5e15ffdd",
            "title": "A Record",
            "artist": "An Artist",
            "date": "1971",
            "format": "Vinyl",
        }
        self.client.post("/collection/add", data=release)
        self.client.post("/collection/add", data=release)
        with self.app.app_context():
            self.assertEqual(CollectionItem.query.count(), 1)
            item_id = CollectionItem.query.one().id
        response = self.client.post(f"/collection/{item_id}/remove")
        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            self.assertEqual(CollectionItem.query.count(), 0)

    def test_other_user_cannot_remove_collection_item(self):
        with self.app.app_context():
            item = CollectionItem(
                user_id=self.other_id,
                musicbrainz_id="76df3287-6cda-33eb-8e9a-044b5e15ffdd",
                artist_name="An Artist",
                release_title="A Record",
            )
            db.session.add(item)
            db.session.commit()
            item_id = item.id
        self.login()
        self.assertEqual(self.client.post(f"/collection/{item_id}/remove").status_code, 404)

    def test_profile_groups_reactions_and_hides_private_posts_from_visitors(self):
        with self.app.app_context():
            user = db.session.get(User, self.user_id)
            subforum = Subforum("Music", "Music discussion")
            public_post = Post("Public signal", "A public post body", datetime.datetime.now())
            private_post = Post(
                "Private signal",
                "A private post body",
                datetime.datetime.now(),
                visibility="private",
            )
            subforum.posts.extend([public_post, private_post])
            user.posts.extend([public_post, private_post])
            db.session.add(subforum)
            db.session.flush()
            public_reaction = Reaction("like")
            private_reaction = Reaction("heart")
            public_reaction.user_id = user.id
            public_reaction.post_id = public_post.id
            private_reaction.user_id = user.id
            private_reaction.post_id = private_post.id
            db.session.add_all([public_reaction, private_reaction])
            db.session.commit()

        visitor_response = self.client.get("/users/soundartist?tab=reactions")
        self.assertEqual(visitor_response.status_code, 200)
        self.assertIn(b"Public signal", visitor_response.data)
        self.assertNotIn(b"Private signal", visitor_response.data)

        self.login()
        member_response = self.client.get("/users/soundartist?tab=reactions")
        self.assertIn(b"Public signal", member_response.data)
        self.assertIn(b"Private signal", member_response.data)


class MusicBrainzClientTests(unittest.TestCase):
    def test_release_search_is_normalized(self):
        payload = {
            "releases": [{
                "id": "76df3287-6cda-33eb-8e9a-044b5e15ffdd",
                "title": "Journey in Satchidananda",
                "date": "1971",
                "country": "US",
                "artist-credit": [{"name": "Alice Coltrane", "joinphrase": ""}],
                "media": [{"format": "12\" Vinyl"}],
                "release-group": {"id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"},
            }]
        }

        class Response(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *args):
                self.close()

        with patch("forum.musicbrainz.urlopen", return_value=Response(json.dumps(payload).encode())):
            with patch("forum.musicbrainz.time.sleep"), patch("forum.musicbrainz._exact_artist", return_value=None):
                results = search_releases("Alice Coltrane")
        self.assertEqual(results[0]["artist"], "Alice Coltrane")
        self.assertEqual(results[0]["format"], '12" Vinyl')
        self.assertIn(results[0]["id"], results[0]["cover_url"])

    def test_exact_artist_is_prioritized_and_editions_are_grouped(self):
        payload = {
            "releases": [
                {
                    "id": "11111111-1111-1111-1111-111111111111",
                    "title": "Prince",
                    "score": 100,
                    "artist-credit": [{"name": "Another Artist", "joinphrase": ""}],
                    "release-group": {"id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"},
                },
                {
                    "id": "22222222-2222-2222-2222-222222222222",
                    "title": "Purple Rain",
                    "score": 90,
                    "artist-credit": [{"name": "Prince", "joinphrase": ""}],
                    "release-group": {"id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"},
                },
                {
                    "id": "33333333-3333-3333-3333-333333333333",
                    "title": "Purple Rain",
                    "score": 89,
                    "artist-credit": [{"name": "Prince", "joinphrase": ""}],
                    "release-group": {"id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"},
                },
            ]
        }

        class Response(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *args):
                self.close()

        with patch("forum.musicbrainz.urlopen", return_value=Response(json.dumps(payload).encode())):
            with patch("forum.musicbrainz.time.sleep"), patch("forum.musicbrainz._exact_artist", return_value=None):
                results = search_releases("Prince")
        self.assertEqual(results[0]["artist"], "Prince")
        self.assertEqual(sum(result["title"] == "Purple Rain" for result in results), 1)


if __name__ == "__main__":
    unittest.main()
