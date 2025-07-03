from flask import Blueprint

bp = Blueprint('admin_panel', __name__)

from . import routes
