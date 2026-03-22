from flask import Blueprint, render_template, request, jsonify

from services.tfr_service import (
    get_all_tfr,
    create_tfr,
    update_tfr,
    delete_tfr,
    get_tfr_summary,
    get_latest_tfr,
)

tfr_bp = Blueprint("tfr_bp", __name__, url_prefix="/tfr")


@tfr_bp.route("/", methods=["GET"])
def index():
    """Render the TFR page with all records, summary, and latest."""
    records_raw = get_all_tfr()
    records = [dict(r) for r in records_raw] if records_raw and not isinstance(records_raw, dict) else []
    summary = get_tfr_summary()
    latest = get_latest_tfr()
    return render_template(
        "tfr.html",
        records=records,
        summary=summary,
        latest=latest,
        active_page="tfr",
    )


@tfr_bp.route("/", methods=["POST"])
def create():
    """Create a new TFR record."""
    try:
        data = request.get_json()
        result = create_tfr(data)
        if "error" in result:
            return jsonify({"success": False, "error": result["error"]}), 400
        return jsonify({"success": True, "data": result}), 201
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@tfr_bp.route("/<int:id>", methods=["PUT"])
def update(id):
    """Update an existing TFR record."""
    try:
        data = request.get_json()
        result = update_tfr(id, data)
        if "error" in result:
            return jsonify({"success": False, "error": result["error"]}), 400
        return jsonify({"success": True, "data": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@tfr_bp.route("/<int:id>", methods=["DELETE"])
def delete(id):
    """Delete a TFR record."""
    try:
        result = delete_tfr(id)
        if "error" in result:
            return jsonify({"success": False, "error": result["error"]}), 400
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
