# SoundLab Developer Study Plan

## Goal

By the end of this plan, you should be able to give another developer a clear
15-minute architecture walkthrough of SoundLab, trace a browser request from
the UI to the database and back, run the application locally or with Docker,
and identify where a new feature should be implemented and tested.

Use this learning loop for every layer:

1. Read the listed files in order.
2. Run the application and observe that layer.
3. Trace one concrete feature through the code.
4. Explain the layer aloud without looking at this guide.
5. Complete the checkpoint before moving on.

The plan is organized from the outside of the system toward its data core,
then back out through testing and deployment.

## System map

```text
Browser
  |
  | HTTP request / HTML response
  v
Gunicorn (Docker) or Flask development server
  |
  v
forum/app.py -> Flask app created by forum/__init__.py
  |
  +-> Flask-Login: session and current_user
  +-> Blueprints: auth, posts, comments, reactions, messages,
  |                settings, profiles
  +-> Jinja templates -> Bootstrap + forum/static/style.css
  |
  v
Flask-SQLAlchemy models
  |
  +-> SQLite for the simple local workflow
  +-> MySQL 8.4 when database environment variables are supplied
  |
  +-> MusicBrainz and Cover Art Archive for collection search/artwork
```

## Layer 1: Product behavior and repository orientation

Suggested time: 45-60 minutes

Start by learning what the application does before studying how it does it.

Read in this order:

- `README.md`
- `forum/app.py`
- `forum/templates/layout.html`
- `Docs/Circuslab_UML_After.md`
- `Docs/docker.md`

Know the main user-facing features:

- Account creation, login, logout, account settings, password changes, and
  account deletion
- Nested subforums and public/private posts
- Markdown posts, optional image/video links, and comments
- Like, dislike, and heart reactions
- Direct messages and unread state
- Public musician profiles, earned avatars, and MusicBrainz collections
- Author/admin edit and delete permissions

Run the application using one workflow:

```sh
# Existing virtual environment
source venv/bin/activate
./run.sh

# Or Docker after creating .env from .env.example
docker compose up --build
```

Hands-on exercise:

1. Create two accounts.
2. Create one public and one private post.
3. Add a comment and reaction.
4. Send a message between the accounts.
5. Edit a profile and search for a MusicBrainz release.

Teach-back checkpoint:

> SoundLab is a server-rendered music community forum built with Flask. Its
> core entities are users, subforums, posts, comments, reactions, profiles,
> collection items, and private messages. Flask routes process requests,
> SQLAlchemy stores the data, Jinja renders HTML, and Docker can run the app
> with MySQL in a reproducible two-container environment.

## Layer 2: Application startup and configuration

Suggested time: 60 minutes

Read:

- `forum/__init__.py`
- `forum/app.py`
- `config.py`
- `.env.example`
- `run.sh`
- `Procfile`

Understand the startup sequence:

1. `forum.app` calls `create_app()`.
2. `create_app()` creates Flask and loads `config.Config`.
3. It registers the Markdown template filter and all feature blueprints.
4. It connects the shared SQLAlchemy object and creates missing tables.
5. `forum/app.py` configures Flask-Login and its `user_loader`.
6. On an empty database, it creates the initial subforums.
7. The `/` route queries root subforums and renders `subforums.html`.

Be able to explain configuration selection:

- With `DATABASE_USER` and `DATABASE_NAME`, `config.py` constructs a
  `mysql+pymysql` URL. Docker supplies these values and uses host `db`.
- Without those required values, the app falls back to SQLite at
  `instance/circuscircus.db`.
- `SECRET_KEY` signs session data. Real deployments must override the fallback.
- `.env` is private and ignored; `.env.example` documents required variables.

Hands-on exercise:

```sh
venv/bin/python -c "from forum.app import app; print(app.url_map)"
```

Identify which endpoint belongs to the base app and which endpoints come from
blueprints.

Teach-back checkpoint:

Explain why `forum.app:app` works as the Gunicorn target and why importing a
module can start application initialization.

## Layer 3: Backend routes and request lifecycle

Suggested time: 2-3 hours

Read one blueprint at a time:

| Feature | Python module | Important endpoints |
| --- | --- | --- |
| Authentication | `forum/auth.py` | `/loginform`, `/action_login`, `/action_logout`, `/action_createaccount` |
| Posts | `forum/posts.py` | `/subforum`, `/addpost`, `/viewpost`, `/action_post`, `/posts/<id>/edit`, `/posts/<id>/delete` |
| Comments | `forum/comments.py` | `/action_comment`, `/comments/<id>/edit`, `/comments/<id>/delete` |
| Reactions | `forum/reactions.py` | `/action_reaction` |
| Messages | `forum/messages.py` | `/messages/`, `/messages/send`, `/messages/conversation/<id>` |
| Settings | `forum/settings.py` | `/settings`, `/action_settings`, `/settings/password`, `/settings/delete` |
| Profiles | `forum/profiles.py` | `/users/<username>`, `/profile/edit`, `/collection/*` |

For every route, answer these questions:

1. Which HTTP method and URL invoke it?
2. Is `@login_required` used?
3. Does input come from `request.args`, `request.form`, or the URL path?
4. Which validation and authorization checks run?
5. Which models are queried or changed?
6. Does the route render, redirect, or abort with an HTTP error?

Trace the create-post request completely:

```text
createpost.html form
  -> POST /action_post?sub=<id>
  -> login_required
  -> find Subforum
  -> validate title/content/visibility/media
  -> create Post
  -> attach it to current_user and Subforum
  -> db.session.commit()
  -> redirect to /viewpost?post=<new id>
  -> query post/comments/reactions
  -> render viewpost.html
```

Important backend rules to explain:

- Logged-out users cannot discover private posts in listings or by direct URL.
- A post/comment author or an administrator may edit or delete it.
- One reaction exists per user/post; clicking it again removes it, while a
  different reaction changes it.
- Login state is managed by Flask-Login and exposed as `current_user`.
- Passwords are stored as Werkzeug hashes, never as the submitted plaintext.
- User Markdown is rendered and sanitized before it is marked safe for Jinja.
- Media embeds accept only validated HTTPS image links and allowlisted
  YouTube/Vimeo formats.

Hands-on exercise:

Add temporary breakpoints (or use a debugger) in `posts.action_post` and
`posts.viewpost`. Create a post and inspect `request.form`, `current_user`, the
new `Post`, and the redirect response. Remove breakpoints afterward.

Teach-back checkpoint:

Without looking at the code, narrate the create-post flow and name every place
where invalid or unauthorized input can be stopped.

## Layer 4: Database and domain model

Suggested time: 2 hours

Read:

- `forum/models.py`
- The `Message` model at the top of `forum/messages.py`
- `Docs/Circuslab_UML_After.md`
- `scripts/add_post_media.py`
- `scripts/add_post_visibility.py`

Learn this relationship map:

```text
User 1 ---- * Post * ---- 1 Subforum
User 1 ---- * Comment * - 1 Post
User 1 ---- * Reaction * - 1 Post
User 1 ---- 0..1 Profile
User 1 ---- * CollectionItem
User 1 ---- * Message (sender)
User 1 ---- * Message (recipient)
Subforum 1 - * Subforum (parent/children)
```

Know the integrity rules:

- Usernames and emails are unique.
- A user has at most one profile.
- A user has at most one reaction per post.
- Reactions are limited to `like`, `dislike`, and `heart`.
- Visibility is limited to `public` and `private`.
- A MusicBrainz release can appear only once in each user's collection.
- User deletion cascades through posts, comments, reactions, profile, and
  collection items. Post deletion cascades through comments and reactions.
- Messages use two foreign keys to `User`, so their sender and recipient
  relationships must be declared separately.

Understand the unit-of-work pattern:

```python
object = Model(...)
db.session.add(object)       # or attach through a relationship
db.session.commit()          # writes the transaction
```

Also understand the limits of `db.create_all()`: it creates missing tables but
does not safely evolve existing columns or constraints. The two scripts are
manual schema upgrades; a production-grade next step would be a migration tool
such as Flask-Migrate/Alembic.

Hands-on exercise:

Draw the model from memory. For each foreign key, point from the child row to
the parent row and explain what should happen when the parent is deleted.

Teach-back checkpoint:

Explain why the uniqueness constraints belong in the database even though the
routes also validate behavior.

## Layer 5: Frontend rendering and styling

Suggested time: 2 hours

Read:

- `forum/templates/layout.html`
- `forum/templates/header.html`, `sidebar.html`, and `footer.html`
- `forum/templates/subforums.html`, `subforum.html`, and `viewpost.html`
- `forum/templates/_user_badge.html` and `_musician_avatar.html`
- `forum/static/style.css` by section, not all at once

Understand the rendering approach:

- This is server-rendered HTML, not a React/Vue single-page application.
- Every full page extends `layout.html` and fills a Jinja `{% block %}`.
- `layout.html` composes the shared header, sidebar, content, errors, and footer.
- Reusable avatar/badge partials prevent author markup from being duplicated.
- Jinja expressions output values; Jinja statements control loops, conditions,
  includes, and URL generation.
- Bootstrap supplies baseline components and the later `style.css` overrides
  them with SoundLab's editorial/arcade visual system.
- Most interactions are normal HTML forms and redirects. The small inline
  script in `viewpost.html` shows and hides the add-comment form.

Study `style.css` in these layers:

1. Root design tokens: colors, borders, spacing, and typography
2. Global shell: header, sidebar, content frame, and footer
3. Shared Bootstrap overrides: panels, buttons, forms, and alerts
4. Forum directory and channel screens
5. Post reader, reactions, comments, forms, account screens, profile, and
   responsive rules

Trace template data:

```text
posts.viewpost() builds:
  post, path, comments, reaction_counts, current_reaction, video_embed_url
                         |
                         v
                  viewpost.html
                         |
                         +-> _user_badge.html
                                  |
                                  +-> _musician_avatar.html
```

Hands-on exercise:

Use browser developer tools to select a post card. For each important CSS rule,
identify whether it comes from Bootstrap or `style.css`, then resize the page
and inspect the responsive layout.

Teach-back checkpoint:

Explain how a username and earned avatar travel from a SQLAlchemy `User` object
through a route and nested Jinja partials into styled HTML.

## Layer 6: Profiles and external services

Suggested time: 90 minutes

Read:

- `forum/profiles.py`
- `forum/musicbrainz.py`
- `forum/templates/profile.html`
- `forum/templates/edit_profile.html`
- `forum/templates/collection_search.html`

Understand avatar progression:

- Starter avatars require zero qualifying posts.
- Color tiers unlock at configured post-count thresholds.
- Headliner avatars unlock at higher individual thresholds.
- A qualifying post must be public, old enough, sufficiently substantial, and
  not duplicate content.
- The server checks earned status again when saving; a user cannot unlock an
  avatar merely by forging form data.

Understand the MusicBrainz boundary:

- SoundLab calls the public MusicBrainz API with a descriptive User-Agent.
- Requests are rate-limited with a lock and minimum interval.
- Exact artists are resolved first; general release searches are normalized
  and grouped to reduce duplicate editions.
- API failures become a controlled `MusicBrainzUnavailable` message.
- Collection rows store a stable MusicBrainz release-group ID and presentation
  metadata; cover art uses the Cover Art Archive URL.

Hands-on exercise:

Trace a collection search from the query string to `_get_json()`, then from a
selected result's POST form to the `CollectionItem` uniqueness constraint.

Teach-back checkpoint:

Explain which data belongs to SoundLab, which comes from MusicBrainz, and how
the application behaves when that external service is unavailable.

## Layer 7: Docker and runtime architecture

Suggested time: 90 minutes

Read:

- `Dockerfile`
- `docker-compose.yml`
- `.dockerignore`
- `.env.example`
- `Docs/docker.md`

Be able to define:

- **Image:** immutable package built from the Dockerfile
- **Container:** running instance of an image
- **Volume:** persistent storage independent of a container
- **Compose service:** configuration for a container role
- **Health check:** command used to determine service readiness/health

Trace the container startup sequence:

```text
docker compose up --build
  -> build web from python:3.12-slim
  -> install requirements in a cached image layer
  -> copy application into /app
  -> start MySQL 8.4 with mysql_data volume
  -> wait for db health check
  -> start Gunicorn: forum.app:app on container port 5000
  -> publish web on localhost:${APP_PORT:-9301}
  -> publish MySQL on localhost:${DB_PORT:-9302}
```

Explain networking precisely:

- The browser uses `localhost:9301` on the Mac.
- Compose forwards that to port `5000` in `web`.
- `web` does not connect to MySQL through `localhost`; it uses Compose DNS name
  `db` and MySQL's internal port `3306`.
- Publishing port `9302` is for optional host-side database tools.
- `mysql_data` preserves data after `docker compose down`.

Run and explain:

```sh
docker compose up --build
docker compose ps
docker compose logs --follow web
docker compose run --rm web python -m unittest discover -s tests
docker compose down
```

Safety checkpoint:

Explain why `docker compose down` preserves the database but
`docker compose down --volumes` deletes it.

## Layer 8: Testing, debugging, and engineering quality

Suggested time: 2 hours

Read the tests in this order:

1. `tests/test_markdown.py` - small pure-function security tests
2. `tests/test_media.py` - URL validation and embed normalization
3. `tests/test_post_visibility.py` - route/database/template integration
4. `tests/test_management.py` - authorization, editing, deletion, passwords
5. `tests/test_profiles.py` - profiles, rewards, collections, API mocking

Run the suite in the existing environment:

```sh
venv/bin/python -m unittest discover -s tests -v
```

Know the testing pattern:

- Tests create a Flask app with isolated in-memory SQLite.
- A Flask test client makes requests without a real browser or server.
- Fixtures create users and related rows.
- Assertions check HTTP status, rendered HTML, authorization, and database
  state.
- External MusicBrainz calls are mocked so tests remain deterministic.

Debug a failure layer by layer:

1. Reproduce the exact request and record its status/response.
2. Find the matching route in `app.url_map`.
3. Check authentication, input validation, and authorization branches.
4. Inspect the SQLAlchemy query and transaction.
5. Check the template context and rendered markup.
6. Check CSS only after the correct HTML exists.
7. Add or update a regression test before declaring the issue fixed.

Teach-back checkpoint:

Choose one test and explain which production contract it protects and what bug
could escape if that test did not exist.

## Eight-session schedule

| Session | Focus | Deliverable |
| --- | --- | --- |
| 1 | Product tour and repository map | Two-minute product explanation |
| 2 | Startup, configuration, and URL map | Draw startup sequence |
| 3 | Auth, posts, comments, reactions | Trace create-post request |
| 4 | Messages, settings, profiles | Explain authorization boundaries |
| 5 | SQLAlchemy model and constraints | Draw ER diagram from memory |
| 6 | Jinja, Bootstrap, custom CSS | Trace one rendered component |
| 7 | Docker, MySQL, environment | Draw container/network diagram |
| 8 | Tests and final teach-back | 15-minute developer walkthrough |

If you have more time, split sessions 3, 4, and 5 into separate days. Do not
move forward merely because a file was read; move forward when you can explain
the checkpoint aloud.

## Final 15-minute developer walkthrough

Use this outline when explaining SoundLab to another developer:

1. **Purpose (1 minute):** SoundLab is a music-centered discussion forum with
   accounts, posts, comments, reactions, messages, profiles, avatars, and music
   collections.
2. **Architecture (2 minutes):** Browser -> Flask/Gunicorn -> blueprints ->
   SQLAlchemy -> SQLite/MySQL, with Jinja generating the HTML.
3. **Startup (2 minutes):** app factory, configuration choice, blueprint
   registration, Flask-Login, table creation, initial subforums.
4. **Request example (3 minutes):** trace create post from HTML form through
   validation, relationships, commit, redirect, query, and template.
5. **Database (2 minutes):** describe core entities, foreign keys, uniqueness,
   checks, and cascades.
6. **Frontend (2 minutes):** layout inheritance, shared partials, Bootstrap,
   custom CSS, and server-rendered forms.
7. **Docker (2 minutes):** web/db services, ports, DNS hostname, health checks,
   environment variables, and persistent volume.
8. **Quality (1 minute):** sanitization, permissions, tests, external API
   handling, and current migration limitation.

## Questions you should be able to answer

- Why is a Flask blueprint useful in this project?
- What is the difference between `request.args` and `request.form`?
- How does Flask-Login turn a session into `current_user`?
- Why does a private post return 404 to a logged-out direct request?
- What prevents two reactions by the same user on one post?
- What is the difference between route validation and a database constraint?
- Why is sanitized Markdown returned as `Markup`?
- How does Jinja template inheritance reduce duplication?
- Why does Docker use `db` rather than `localhost` as the database hostname?
- Why does Compose wait for a healthy database instead of only a started one?
- What survives `docker compose down`, and why?
- Why is `db.create_all()` not a complete migration strategy?
- How would you add a new feature while preserving authorization and tests?

## Definition of ready

You are ready to explain SoundLab when you can do all of the following without
reading a script:

- Draw the system and database maps.
- Trace login and create-post requests end to end.
- Locate the route, model, template, CSS, and test for a feature.
- Explain public/private visibility and author/admin permissions.
- Explain safe Markdown and media handling.
- Explain the Docker image, two containers, network, ports, health checks, and
  persistent volume.
- Run the full test suite and interpret a failure by architectural layer.
- Identify one current improvement: formal database migrations, CSRF
  protection for state-changing forms, or further separation of app startup.
