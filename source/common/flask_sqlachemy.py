from flask_sqlalchemy import SQLAlchemy

from source.common.models import Base

db = SQLAlchemy(model_class=Base, disable_autonaming=True)
