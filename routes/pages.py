from flask import Blueprint, render_template

bp = Blueprint("pages", __name__)


@bp.route("/")
def index():
    """Render main OPD clinical summary dashboard."""
    return render_template("index.html")
