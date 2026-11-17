from flask import Blueprint, jsonify

import config
from services import llm_client

bp = Blueprint("system", __name__, url_prefix="/api")


@bp.route("/health", methods=["GET"])
def health_check():
    """Return system readiness of hospital REST API and LLM server."""
    online = llm_client.is_online()
    active_model = llm_client.get_model_name() if online else config.LOCAL_LLM_DEFAULT_MODEL
    return jsonify({
        "status": "online",
        "port": config.PORT,
        "hospital_api_host": config.HOSPITAL_API_HOST,
        "local_llm_online": online,
        "local_llm_host": config.LOCAL_LLM_HOST,
        "local_llm_model": active_model,
        "local_llm_engine": "vLLM",
        "gpu_device": "NVIDIA RTX A6000 (48GB VRAM)"
    })
