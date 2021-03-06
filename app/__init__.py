from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_caching import Cache
from . import config

app = Flask(__name__)
app.config.update(config.secrets)

cache = Cache(app, config.secrets)

db = SQLAlchemy()
db.init_app(app)


@app.route('/', methods=['GET'])
def api():
    return jsonify([])


from app.images.views import mod as images_mod
app.register_blueprint(images_mod)