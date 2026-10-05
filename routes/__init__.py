"""HTTP routes, grouped by feature as Flask blueprints."""

from routes.pages import bp as pages_bp
from routes.patient import bp as patient_bp
from routes.drugs import bp as drugs_bp
from routes.ai import bp as ai_bp
from routes.system import bp as system_bp

ALL_BLUEPRINTS = (pages_bp, patient_bp, drugs_bp, ai_bp, system_bp)


def register_blueprints(app):
    for bp in ALL_BLUEPRINTS:
        app.register_blueprint(bp)
