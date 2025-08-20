# __init__.py
from flask import Flask
from flask_cors import CORS
from routes import routes

def create_app():
    app = Flask(__name__)
    CORS(app)  # Enable CORS for frontend
    app.register_blueprint(routes)
    return app
