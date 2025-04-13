from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix

from source.api.app_factory import create_app

app = create_app()

# CORS for when running without a proxy
CORS(app, resources={r"/api/*": {"origins": "*"}}, expose_headers=['Content-Disposition'])

# Running behind a proxy in production
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1, x_prefix=1)
