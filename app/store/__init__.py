from flask import Blueprint

store_bp = Blueprint('store', __name__, url_prefix='/store')

from . import routes
