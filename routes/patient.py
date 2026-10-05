import logging

from flask import Blueprint, jsonify, request

import config
from services import mcp_client, summary_engine

bp = Blueprint("patient", __name__, url_prefix="/api")
logger = logging.getLogger("OPD_Summaries")

DEFAULT_CLINIC_DATE = "2026/09/01"


@bp.route("/roster", methods=["GET"])
def get_roster():
    """Return outpatient roster loaded from Cloud_Data."""
    try:
        roster = mcp_client.load_patient_roster()
        return jsonify({"status": "success", "count": len(roster), "patients": roster})
    except Exception as e:
        logger.error(f"Error loading roster: {e}")
        return jsonify({"status": "error", "message": str(e), "patients": []}), 500


@bp.route("/patient/<id_no>", methods=["GET"])
def get_patient_summary(id_no):
    """Generate and return full clinical summary for a patient."""
    clinic_date = request.args.get("date", DEFAULT_CLINIC_DATE).strip()
    try:
        daterange = int(request.args.get("daterange", config.DEFAULT_DATERANGE))
    except ValueError:
        return jsonify({"status": "error", "message": "daterange must be an integer"}), 400

    try:
        return jsonify(summary_engine.generate_patient_summary(id_no, clinic_date, daterange))
    except Exception as e:
        logger.error(f"Error generating summary for {id_no}: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500
