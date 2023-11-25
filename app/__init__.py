from flask import Flask
from flask_sqlalchemy import SQLAlchemy


app = Flask(__name__)
app.config.from_object('config')

UPLOAD_FOLDER = '.\\tmp'
ALLOWED_EXTENSIONS = {'wav', 'mp3'}

from app import views
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
