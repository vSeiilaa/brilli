# app/__init__.py

from flask import Flask
from flask_wtf import CSRFProtect
from dotenv import load_dotenv
import os

load_dotenv()
secret_key = os.getenv('FLASK_SECRET_KEY')

app = Flask(__name__)

app.secret_key = secret_key

# Initialize CSRF protection
csrf = CSRFProtect(app)

# Import routes
from app import routes
