from flask import Flask
smeli_app = Flask(__name__)
from smeli_web import routes
