from app import create_app
from app.models import Machine, Manifest, Base
from app.extensions import db
app = create_app()

def start():
    try:
        with app.app_context():
            Base.metadata.create_all(bind=db.engine)
        print("DB started!")
    except Exception as e:
        print(f"[ERROR]: {e}")
        

def restart():
    try:
        with app.app_context():
            Base.metadata.drop_all(bind=db.engine)
            Base.metadata.create_all(bind=db.engine)
        print("DB reset")
    except Exception as e:
        print(f"[ERROR]: {e}")
        

