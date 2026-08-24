# SoundLab Docker guide

## The architecture

Docker Compose runs two separate services on one private network:

```text
Browser -> localhost:9301 -> web container -> db:3306 -> MySQL container
Database client -> localhost:9302 ----------------------^        |
                                                MySQL data -> mysql_data volume
```

- `web` is the SoundLab image built from the `Dockerfile`. Gunicorn serves the
  Flask application on port 5000 inside this container.
- `db` uses the official MySQL 8.4 image. Compose DNS makes the service name
  `db` work as its hostname inside the Docker network.
- `mysql_data` is a named volume. Containers can be replaced, while the MySQL
  files in this volume remain.
- Port mappings publish the web app as `localhost:9301` and MySQL as
  `localhost:9302` on the Mac.

An **image** is the reusable package described by a Dockerfile. A **container**
is a running instance of an image. A **volume** stores data independently of a
container. Compose records how all of these pieces run together.

## First-time setup

1. Install and start Docker Desktop.
2. Clone the repository and open a terminal in its root directory.
3. Copy `.env.example` to `.env`.
4. Replace every placeholder in `.env`. Each teammate may use different local
   secrets because `.env` is ignored by Git.
5. Build and start both services:

   ```sh
   docker compose up --build
   ```

6. Wait until the logs show Gunicorn listening, then visit
   <http://localhost:9301>.

The first run downloads the base images and initializes MySQL, so it is slower.
Later runs reuse cached image layers and the existing database volume.

## What happens during startup

1. Compose creates a private network and the `mysql_data` volume.
2. MySQL creates the database and application user from the environment values.
3. Compose runs `mysqladmin ping` until the database reports healthy.
4. Only then does Compose start `web` because its dependency requires a healthy
   database.
5. Flask reads `DATABASE_HOST=db` and constructs a `mysql+pymysql` SQLAlchemy
   connection.
6. The application creates any missing tables, and Gunicorn accepts web traffic.

## Everyday commands

```sh
# Start and show live logs
docker compose up

# Start in the background
docker compose up --detach

# Show container health and port mappings
docker compose ps

# Follow only the Flask/Gunicorn logs
docker compose logs --follow web

# Run all tests in a temporary app container
docker compose run --rm web python -m unittest discover -s tests

# Stop and remove containers and their network
docker compose down
```

`docker compose down` is safe for the database volume. Adding `--volumes`
deletes `mysql_data` and therefore deletes the Dockerized local database. Use
that option only when an intentional clean reset is required.

## When files change

- Python or template changes require `docker compose up --build` because source
  code is copied into the image.
- A changed `requirements.txt` also requires a rebuild. Docker can reuse the
  earlier layers but reinstalls the dependency layer.
- Environment changes require the containers to be recreated with
  `docker compose up --detach --force-recreate`.

## Common problems

- **Docker command is missing:** start Docker Desktop and finish its first-run
  setup. If necessary, enable its command-line tool installation in Settings.
- **Cannot connect to the Docker daemon:** Docker Desktop is not fully started.
- **Port is already allocated:** change `APP_PORT` or `DB_PORT` in `.env`, then
  recreate the services. The app URL must use the configured `APP_PORT`.
- **Database authentication fails after changing `.env`:** MySQL initialization
  variables only apply when the volume is empty. Restore the original values or,
  if the data is disposable, intentionally reset it with
  `docker compose down --volumes` and start again.
- **Web does not start:** use `docker compose ps` and
  `docker compose logs db web`. The database health check must pass first.

## Short instructor explanation

The Dockerfile creates a reproducible Python 3.12 application image and starts
Flask with Gunicorn. Compose runs that image beside an official MySQL 8.4 image.
It passes database settings through environment variables, connects the services
over a private network using `db` as the hostname, waits for MySQL to become
healthy, publishes the web app on port 9301 and MySQL on port 9302, and persists
database files in a named volume. Secrets stay in an ignored local `.env` file
rather than in Git or the application image.
