# Stage 1: Build virtual env
FROM python:3.10-slim AS builder

# Install dependencies (keep in one statement and clean up so the layer will be cached)
RUN apt update && apt install -y  \
    build-essential \
    python3-dev \
    libffi-dev \
    libxml2 \
    libxml2-dev \
    libxslt1-dev  \
    pkg-config \
    default-libmysqlclient-dev \
    && apt clean \
    && rm -rf /var/lib/apt/lists/*

# Install Pipenv
RUN pip install --upgrade pip && pip install pipenv

# Create app user (to match the user in the final image)
RUN adduser --disabled-password --gecos "" --home /app app

USER app

WORKDIR /app

# Install Python packages
COPY Pipfile.lock ./

# Using .venv dir for better caching
RUN PIPENV_VENV_IN_PROJECT=1 pipenv --python 3.10 sync

# Stage 2: Run with source and built virtual env from builder
FROM python:3.10-slim

RUN apt update && apt upgrade -y \
    && apt install -y \
    libstdc++6 \
    curl \
    libmariadb3 \
    libmagic1 \
    wkhtmltopdf \
    && apt clean

# Create app user
RUN adduser --disabled-password --gecos "" --home /app app

USER app

WORKDIR /app

# Copy virtual environment from builder stage
COPY --from=builder /app/.venv /app/.venv

# Update PATH to include the .venv binaries
ENV PATH="/app/.venv/bin:$PATH"

# Download NLTK data
RUN python -m nltk.downloader punkt punkt_tab stopwords

# Copy default Gunicorn config file
COPY --chown=app:app dockerfiles/config/gunicorn.conf.py .

# Copy source
COPY --chown=app:app api_wsgi.py .
COPY --chown=app:app source/common source/common
COPY --chown=app:app source/api source/api

ENV PYTHONUNBUFFERED=TRUE
ENV FLASK_APP=app_wsgi

# Gunicorn binds to this port
EXPOSE 8000

# Run
CMD ["gunicorn", "api_wsgi:app", "--config", "gunicorn.conf.py"]
