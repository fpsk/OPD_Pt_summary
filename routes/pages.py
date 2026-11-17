from flask import Blueprint, current_app, render_template

from routes.patient import DEFAULT_CLINIC_DATE
from clinical_common.launch import get_last_query

bp = Blueprint("pages", __name__)


@bp.route("/")
def index():
    """Render main OPD clinical summary dashboard."""
    is_testing = bool(current_app.config.get("TESTING"))
    last_q = get_last_query(
        default_date=DEFAULT_CLINIC_DATE,
        default_patient_id="B100134889",
        use_disk=not is_testing,
    )
    return render_template(
        "index.html",
        default_date=last_q["patient_date"],
        default_patient_id=last_q["patient_id"],
    )
