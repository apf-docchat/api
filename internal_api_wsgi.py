from werkzeug.middleware.proxy_fix import ProxyFix

from source.internal_api.app_factory import create_app

app = create_app()

# Running behind a proxy in production
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1, x_prefix=1)
