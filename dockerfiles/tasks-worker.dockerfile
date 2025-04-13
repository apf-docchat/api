# Stage 1: Build virtual env
FROM python:3.12-alpine AS builder

# Install dependencies
RUN apk update && apk add --no-cache \
    build-base \
    linux-headers \
    python3-dev \
    libffi-dev \
    libxml2 \
    libxml2-dev \
    libxslt-dev

# Install Pipenv
RUN pip install --upgrade pip && pip install pipenv

# Create app user (to match the user in the final image)
RUN adduser --home /app --disabled-password app

USER app

WORKDIR /app

# Install Python packages
COPY Pipfile.lock ./

# Using .venv dir for better caching
RUN PIPENV_VENV_IN_PROJECT=1 pipenv --python 3.12 sync --categories tasks-worker

# Stage 2: Run with source and built virtual env from builder
FROM python:3.12-alpine

# Install runtime dependencies
RUN apk update && apk add --no-cache \
    libstdc++

# Create app user
RUN adduser --home /app --disabled-password app

USER app

WORKDIR /app

# Copy virtual environment from builder stage
COPY --from=builder /app/.venv /app/.venv

# Update PATH to include the .venv binaries
ENV PATH="/app/.venv/bin:$PATH"

# Copy source
COPY --chown=app:app tasks_worker.py .
COPY --chown=app:app source/tasks source/tasks

# Run
CMD ["celery", "--app=tasks_worker", "worker", "--loglevel=INFO"]
