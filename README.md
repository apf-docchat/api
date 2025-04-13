# API Service

Contains API Server, API Background Worker, etc.

## Services

- API Server
- [API Background Worker](README.worker.md)

## Running in a Codespace

_When the Codespace is created, the required services (MySQL, MongoDB, Redis, etc.) are automatically installed and
initialized with seed data._

### Setup

- Wait for a couple of minutes for the Codespace to be ready (you'll see `.env` created in the file explorer)
- Add correct values for the config variables in `config.py`
- Add correct values for `OPENAI_` and `PINECONE_` keys in the `.env` file
- Setup Python virtual environment and install dependencies:

```shell
pipenv --python 3.10
pipenv install
pipenv shell
```

### Running

```shell
pipenv shell
flask run
```

- In the `Ports` tab in VS Code, you can click the globe icon in the `Forwarded Address` column for port `5000` to see the web UI load
