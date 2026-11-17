import os

from flask import Blueprint, Response, jsonify, request

from services import drug_photo_service, drug_safety_service

bp = Blueprint("drugs", __name__, url_prefix="/api")


def _arg(name: str) -> str:
    return request.args.get(name, "").strip()


@bp.route("/drug_photo", methods=["GET"])
def get_drug_photo():
    """Stream pill photo from pills_jpeg_archive.zip or disk."""
    stem = _arg("img_id")
    if not stem:
        prod = drug_photo_service.find_drug_product(_arg("code"), _arg("brand"))
        if prod and prod.get("local_image_path"):
            stem = os.path.splitext(os.path.basename(prod["local_image_path"]))[0]

    if not stem:
        return Response("Photo not found", status=404, mimetype="text/plain")

    content, mime = drug_photo_service.get_photo_bytes(stem)
    if not content:
        return Response("Photo binary not found", status=404, mimetype="text/plain")

    return Response(
        content,
        mimetype=mime,
        headers={
            "Cache-Control": "public, max-age=86400",
            "Content-Disposition": f"inline; filename={stem}.jpg"
        }
    )


@bp.route("/drug_info", methods=["GET"])
def get_drug_info():
    """Return structured drug appearance details, NHI code, and photo URL."""
    return jsonify(drug_photo_service.get_drug_info_payload(_arg("code"), _arg("brand"), _arg("generic")))


@bp.route("/drug_safety", methods=["GET"])
def get_drug_safety():
    """Return comprehensive clinical drug safety information (dosing, renal adjustment, side effects, contraindications, pregnancy warnings)."""
    return jsonify(drug_safety_service.get_safety_profile(_arg("code"), _arg("brand"), _arg("generic")))
