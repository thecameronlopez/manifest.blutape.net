from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_migrate import Migrate

from app.models import Base
db = SQLAlchemy(model_class=Base)
cors = CORS()
migrate = Migrate()
