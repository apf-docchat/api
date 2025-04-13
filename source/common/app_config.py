from dynaconf import Dynaconf

config = Dynaconf()

# Load config defaults file
config.load_file('config.defaults.toml', silent=False)

# Load config overrides file
config.load_file('config.overrides.toml', silent=True)
