from flask import render_template
from . import frontend_bp


@frontend_bp.route('/')
def index():
    return render_template('index.html')
