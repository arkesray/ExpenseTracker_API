from flask import Flask 
from flask_sqlalchemy import SQLAlchemy 

db = SQLAlchemy()

def create_app(debug=False):
    app = Flask(__name__)
    app.config.from_pyfile('config.py')

    app.debug = debug
    
    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint, url_prefix='/')

    from .models import db
    db.init_app(app)
    
    with app.app_context():
        db.create_all()
    return app
