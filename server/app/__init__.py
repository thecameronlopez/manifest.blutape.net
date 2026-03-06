from flask import Flask
from app.extensions import db, cors
from config import Config


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    db.init_app(app)
    cors.init_app(app)
    
    from app.api import api
    app.register_blueprint(api)
    
    
    
    
    return app