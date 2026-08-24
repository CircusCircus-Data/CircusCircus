FROM python:3.12-slim

# Keep Python logs visible in Docker and prevent .pyc cache files.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install dependencies in a separate layer so Docker can cache them.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application only after dependencies are installed.
COPY . .

EXPOSE 5000

# Gunicorn serves Flask on every container network interface.
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--threads", "4", "--access-logfile", "-", "forum.app:app"]
