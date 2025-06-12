from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from os import environ

# Import your extensions and blueprints
from app.models.user import db  # SQLAlchemy instance
from app.routes.auth import auth
from app.routes.views import views
from app.routes.youtube_auth import youtube_bp

def create_app():
    # Load environment variables from .env file
    load_dotenv()

    # Create Flask app
    app = Flask(__name__)

    # Basic Configurations
    app.secret_key = environ.get('SECRET_KEY', 'dev-secret-key')
    app.config['SQLALCHEMY_DATABASE_URI'] = environ.get('DATABASE_URL', 'sqlite:///site.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['ENV'] = environ.get('FLASK_ENV', 'development')

    # Initialize database with app
    db.init_app(app)

    # Register Blueprints
    app.register_blueprint(auth, url_prefix='/')
    app.register_blueprint(views, url_prefix='/')
    app.register_blueprint(youtube_bp, url_prefix='/youtube')

    # Create database tables
    with app.app_context():
        db.create_all()

    return app
