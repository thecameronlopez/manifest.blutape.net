from flask import Blueprint
from .auth import auth as auth_bp
from .manifest import manifest as man_bp

api = Blueprint("api", __name__, url_prefix="/api")

api.register_blueprint(auth_bp)
api.register_blueprint(man_bp, url_prefix="/manifest")
