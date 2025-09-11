"""
Web interface module for CryptoChecker Gaming Platform.
Contains Flask web application, API endpoints, WebSocket integration, and frontend components.
"""

__version__ = "3.0.0"

# Flask App Configuration
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO
from flask_login import LoginManager
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize extensions
db = SQLAlchemy()
socketio = SocketIO()
login_manager = LoginManager()

def create_app():
    """Create and configure Flask application"""
    app = Flask(__name__)
    
    # Basic config
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key-change-in-production')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///crypto_gaming.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize extensions with app
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    
    # Register blueprints
    from .auth.routes import auth_bp
    from .gaming.routes import gaming_bp
    from .gaming.api.roulette import gaming_api
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(gaming_bp)
    app.register_blueprint(gaming_api)
    
    # Setup Socket.IO
    socketio.init_app(app, cors_allowed_origins="*")
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    return app