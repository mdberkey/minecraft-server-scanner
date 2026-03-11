import os
from flask import Flask, render_template, send_from_directory

from app.api.routes import api
from app.db.models import get_engine, Base

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def create_app():
    app = Flask(
        __name__,
        template_folder=os.path.join(BASE_DIR, 'templates'),
        static_folder=os.path.join(BASE_DIR, 'static')
    )
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')

    db_path = os.environ.get('DB_PATH', 'servers.db')
    engine = get_engine(f'sqlite:///{db_path}')
    Base.metadata.create_all(engine)

    app.register_blueprint(api)

    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/favicon.ico')
    def favicon():
        return send_from_directory(app.static_folder, 'favicon.ico')

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=False)
