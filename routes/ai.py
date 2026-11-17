import logging

from flask import Blueprint, jsonify, request

from services import clinical_chat, nlp_engine, summary_engine

bp = Blueprint("ai", __name__, url_prefix="/api")
logger = logging.getLogger("OPD_Summaries")


@bp.route("/extract_ai", methods=["POST"])
def extract_ai():
    """Deep clinical extraction of a report via the local LLM."""
    data = request.get_json(silent=True) or {}
    report_text = (data.get("text") or "").strip()
    modality = data.get("modality", "")

    if not report_text:
        return jsonify({"status": "error", "message": "Report text is required"}), 400

    try:
        return jsonify({"status": "success", "result": nlp_engine.extract_with_local_llm(report_text, modality)})
    except Exception as e:
        logger.error(f"AI extraction failed: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@bp.route("/chat", methods=["POST"])
def chat():
    """Interactive clinical Q&A about the current patient."""
    data = request.get_json(silent=True) or {}
    user_query = (data.get("message") or "").strip()
    if not user_query:
        return jsonify({"status": "error", "message": "請輸入諮詢問題"}), 400

    body, status = clinical_chat.answer(
        summary_engine,
        patient_id=(data.get("patient_id") or "").strip(),
        clinic_date=(data.get("clinic_date") or "1150721").strip(),
        user_query=user_query,
        history=data.get("history") or [],
        logger=logger,
    )
    return jsonify(body), status
