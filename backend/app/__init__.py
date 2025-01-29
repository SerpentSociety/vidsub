from flask import Flask
from flask_cors import CORS
from config.settings import Config
from app.extensions import bcrypt, jwt
from app.core.video_service import VideoService
import os

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Set Groq API key from environment
    app.config['GROQ_API_KEY'] = os.getenv('GROQ_API_KEY')
    
    CORS(app, 
         origins=["http://127.0.0.1:5000", "http://localhost:3000"],
         allow_headers=["*"],
         expose_headers=["*"],
         methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
         supports_credentials=True,
         max_age=3600)
    
    bcrypt.init_app(app)
    jwt.init_app(app)
    
    # Initialize VideoService
    app.video_service = VideoService()
    
    from app.routes.auth import auth_bp
    from app.routes.video import video_bp
    
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(video_bp, url_prefix='/api/video')
    
    return app