import logging
import time

from flask import Blueprint, current_app, jsonify, request

import config
from services import mcp_client, summary_engine
from services.patient_mcp_client import (
    extract_demographics_from_dict,
    to_roc_date,
    to_standard_date,
)
from clinical_common import APP_PORTS
from clinical_common.demographics import LAUNCH_DATE_KEYS, PATIENT_ID_KEYS, lookup_key
from clinical_common.launch import (
    LaunchBroker,
    build_relay_payload,
    get_last_query,
    relay_async,
    set_last_query,
)
from clinical_common.roc_dates import today_roc

bp = Blueprint("patient", __name__, url_prefix="/api")
logger = logging.getLogger("OPD_Summaries")

DEFAULT_CLINIC_DATE = "1150721"
SIBLING_PORTS = (APP_PORTS["fdcs"], APP_PORTS["chb"])

# Push-based patient launch: SSE broker (latest launch retained for 5 minutes)
launch_broker = LaunchBroker()


def format_launch_roc_date(date_val=None) -> str:
    """Convert date into 7-digit ROC string (YYYMMDD); defaults to today if omitted."""
    if date_val is None or not str(date_val).strip():
        return today_roc()
    return to_roc_date(str(date_val))


def _resolve_launch_date(patient_id: str, raw_date) -> str:
    """
    Explicit date wins. Without one, use the last queried patient's date, else a still-pending
    launch for the same patient, else the patient's newest roster clinic day, else today.
    """
    if raw_date is not None and str(raw_date).strip():
        return format_launch_roc_date(raw_date)
    is_testing = bool(current_app.config.get("TESTING"))
    last_date = get_last_query(default_date="", use_disk=not is_testing)["patient_date"]
    if last_date:
        return last_date
    prev = launch_broker.latest_for(patient_id)
    if prev and prev.get("patient_date"):
        return prev["patient_date"]
    roster = mcp_client.roster.get(patient_id)
    if roster.get("clinic_date"):
        return roster["clinic_date"]
    return format_launch_roc_date(None)


def handle_launch_request():
    """Shared handler for POST /launch and POST /api/launch. Never logs patientID."""
    payload = request.get_json(force=True, silent=True)
    if not isinstance(payload, dict) or not payload:
        payload = request.form.to_dict() or request.args.to_dict() or {}

    raw_id = lookup_key(payload, PATIENT_ID_KEYS)
    if not raw_id or not str(raw_id).strip():
        return jsonify({"status": "error", "message": "patientID is required."}), 400

    patient_id = str(raw_id).strip().upper()
    patient_date = _resolve_launch_date(patient_id, lookup_key(payload, LAUNCH_DATE_KEYS))

    demo_fields = extract_demographics_from_dict(payload, reference_date=patient_date)
    demo = mcp_client.update_patient_demographics(
        patient_id,
        chart_no=demo_fields.get("chart_no"),
        birth_date=demo_fields.get("birth_date"),
        age=demo_fields.get("age"),
        name=demo_fields.get("name"),
        gender=demo_fields.get("gender"),
        reference_date=patient_date,
    )
    resolved = {k: demo.get(k) or demo_fields.get(k) for k in ("chart_no", "birth_date", "age", "name", "gender")}

    data = {
        "patient_id": patient_id,
        "patient_date": patient_date,
        "standard_date": to_standard_date(patient_date),
        "launch_ts": int(time.time() * 1000),
    }
    if resolved["chart_no"]:
        data["chart_no"] = data["chartNo"] = str(resolved["chart_no"])
    if resolved["birth_date"]:
        data["birth_date"] = data["birthdate"] = str(resolved["birth_date"])
    if resolved["age"] not in (None, ""):
        try:
            data["age"] = int(round(float(resolved["age"])))
        except (TypeError, ValueError):
            data["age"] = resolved["age"]
    if resolved["name"]:
        data["name"] = str(resolved["name"])
    if resolved["gender"]:
        data["gender"] = str(resolved["gender"])

    delivered = launch_broker.publish(data)
    is_testing = bool(current_app.config.get("TESTING"))
    set_last_query(patient_date=patient_date, patient_id=patient_id, persist=not is_testing)

    if not payload.get("relayed"):
        relay_async(
            build_relay_payload(
                payload, patient_id, patient_date,
                chart_no=resolved["chart_no"], birth_date=resolved["birth_date"], age=data.get("age"),
                name=resolved["name"], gender=resolved["gender"],
            ),
            SIBLING_PORTS,
        )

    logger.info(f"POST /launch accepted (date={patient_date}, keys={sorted(payload.keys())}, delivered to {delivered} client(s)).")
    resp_body = {"status": "ok", "delivered": delivered, "patient_date": patient_date}
    for key in ("chart_no", "age", "birth_date"):
        if key in data:
            resp_body[key] = data[key]
    return jsonify(resp_body), 200


@bp.route("/launch", methods=["POST"])
def api_launch_patient():
    return handle_launch_request()


@bp.route("/launch/current", methods=["GET"])
def api_current_launch():
    """Return the active launched patient context if within the retention window, plus last queried date."""
    is_testing = bool(current_app.config.get("TESTING"))
    last_q = get_last_query(
        default_date=DEFAULT_CLINIC_DATE,
        default_patient_id="B100134889",
        use_disk=not is_testing,
    )
    return jsonify({
        "status": "ok",
        "launch": launch_broker.latest(),
        "last_query_date": last_q["patient_date"],
        "last_patient_id": last_q["patient_id"],
    }), 200


@bp.route("/events", methods=["GET"])
def sse_events():
    """Server-Sent Events (SSE) stream for push-based patient launches."""
    return launch_broker.subscribe()


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
    is_testing = bool(current_app.config.get("TESTING"))
    default_date = get_last_query(default_date=DEFAULT_CLINIC_DATE, use_disk=not is_testing)["patient_date"]
    raw_req_date = (request.args.get("date") or "").strip()
    clinic_date = raw_req_date or default_date
    try:
        daterange = int(request.args.get("daterange", config.DEFAULT_DATERANGE))
    except ValueError:
        return jsonify({"status": "error", "message": "daterange must be an integer"}), 400

    demo_params = extract_demographics_from_dict(request.args.to_dict(), reference_date=clinic_date)

    try:
        result = summary_engine.generate_patient_summary(
            id_no,
            clinic_date,
            daterange,
            chart_no=demo_params.get("chart_no"),
            birth_date=demo_params.get("birth_date"),
            age=demo_params.get("age"),
            name=demo_params.get("name"),
            gender=demo_params.get("gender"),
        )
        resolved_date = result.get("clinic_date") or clinic_date
        if result.get("status") != "not_found":
            set_last_query(patient_date=resolved_date, patient_id=id_no, persist=not is_testing)
        elif raw_req_date:
            set_last_query(patient_date=raw_req_date, persist=not is_testing)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error generating summary for {id_no}: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500
