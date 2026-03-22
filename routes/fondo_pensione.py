from flask import Blueprint, render_template, request, jsonify

from services.fp_service import (
    get_all_fp,
    create_fp,
    update_fp,
    delete_fp,
    get_fp_summary,
    get_latest_fp,
)

fp_bp = Blueprint("fp_bp", __name__, url_prefix="/fondo-pensione")


@fp_bp.route("/", methods=["GET"])
def index():
    """Render the fondo pensione page with all records, summary, and latest."""
    records_raw = get_all_fp()
    records = [dict(r) for r in records_raw] if records_raw and not isinstance(records_raw, dict) else []
    summary = get_fp_summary()
    latest = get_latest_fp()
    return render_template(
        "fondo_pensione.html",
        records=records,
        summary=summary,
        latest=latest,
        active_page="fondo_pensione",
    )


@fp_bp.route("/", methods=["POST"])
def create():
    """Create a new fondo pensione record."""
    try:
        data = request.get_json()
        result = create_fp(data)
        if "error" in result:
            return jsonify({"success": False, "error": result["error"]}), 400
        return jsonify({"success": True, "data": result}), 201
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@fp_bp.route("/<int:id>", methods=["PUT"])
def update(id):
    """Update an existing fondo pensione record."""
    try:
        data = request.get_json()
        result = update_fp(id, data)
        if "error" in result:
            return jsonify({"success": False, "error": result["error"]}), 400
        return jsonify({"success": True, "data": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@fp_bp.route("/<int:id>", methods=["DELETE"])
def delete(id):
    """Delete a fondo pensione record."""
    try:
        result = delete_fp(id)
        if "error" in result:
            return jsonify({"success": False, "error": result["error"]}), 400
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
