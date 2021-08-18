from flask import Blueprint

cam = Blueprint('cam', __name__)

from . import views

