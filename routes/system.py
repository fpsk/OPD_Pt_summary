from flask import Blueprint, jsonify

import config
from services import llm_client

bp = Blueprint("system", __name__, url_prefix="/api")


@bp.route("/health", methods=["GET"])
def health_check():
    """Return system readiness of hospital REST API and local LLM."""
    return jsonify({
        "status": "online",
        "port": config.PORT,
        "hospital_api_host": config.HOSPITAL_API_HOST,
        "local_llm_online": llm_client.is_online(),
        "local_llm_host": config.LOCAL_LLM_HOST,
        "local_llm_model": config.LOCAL_LLM_DEFAULT_MODEL,
        "local_llm_engine": "LM Studio",
        "gpu_device": "NVIDIA RTX A6000 (48GB VRAM)"
    })
