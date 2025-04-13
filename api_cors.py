from flask_cors import CORS

from source.api.app_factory import create_app

app = create_app()

# CORS for when running without a proxy
CORS(app, resources={r"/api/*": {"origins": "*"}}, expose_headers=['Content-Disposition'])

if __name__ == "__main__":
    app.run()
