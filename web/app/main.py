from flask import Flask

from config import Config
from database import init_db
from routes.experiments import experiments_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    with app.app_context():
        init_db()

    app.register_blueprint(experiments_bp)

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)