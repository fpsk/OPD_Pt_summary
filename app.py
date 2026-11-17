#!/usr/bin/env python3
"""
OPD Patient Conditions, Findings, and Medications Summarizer App.
Flask server running on port 5008.

Layout:
    config.py    settings (secrets come from .env)
    services/    data access, clinical synthesis, NLP, LLM client, chat
    routes/      Flask blueprints (thin HTTP wrappers over services)
"""

import os
import logging

from flask import Flask

import config
from routes import register_blueprints
from routes.patient import handle_launch_request

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("OPD_Summaries")


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder=os.path.join(config.BASE_DIR, "templates"),
        static_folder=os.path.join(config.BASE_DIR, "static")
    )
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
    register_blueprints(app)
    app.add_url_rule("/launch", view_func=handle_launch_request, methods=["POST"])

    @app.after_request
    def add_no_cache_headers(response):
        from flask import request as req
        if req.path.startswith("/static/js/") or req.path == "/":
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return response

    return app


app = create_app()

if __name__ == "__main__":
    logger.info(f"Starting OPD Summarizer on http://127.0.0.1:{config.PORT}")
    app.run(host="0.0.0.0", port=config.PORT, debug=config.DEBUG, threaded=True)
