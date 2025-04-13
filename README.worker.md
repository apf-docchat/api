# Background Worker

Built using Celery

## System Requirements

- Python 3.11 (Should work with older version. 3.11 is recommended)
- Pipenv
- Redis

## Setup

- `pipenv --python 3.12`
- `pipenv install`
- `cp .env.example .env`
- Modify variables in `.env`

## Usage

- `pipenv shell`
- `celery --app=api_worker worker --loglevel=INFO`
