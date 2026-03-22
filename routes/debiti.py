from flask import Blueprint, render_template, request, jsonify

from services.debiti_service import (
    get_all_debiti,
    create_debito,
    update_debito,
    delete_debito,
    get_debiti_summary,
)

debiti_bp = Blueprint("debiti_bp", __name__, url_prefix="/debiti")


@debiti_bp.route("/", methods=["GET"])
def index():
    """Render the debiti page with all records and summary."""
    records_raw = get_all_debiti()
    records = [dict(r) for r in records_raw] if records_raw and not isinstance(records_raw, dict) else []
    summary = get_debiti_summary()
    return render_template(
        "debiti.html",
        records=records,
        summary=summary,
        active_page="debiti",
    )


@debiti_bp.route("/", methods=["POST"])
def create():
    """Create a new debito record."""
    try:
        data = request.get_json()
        result = create_debito(data)
        if "error" in result:
            return jsonify({"success": False, "error": result["error"]}), 400
        return jsonify({"success": True, "data": result}), 201
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@debiti_bp.route("/<int:id>", methods=["PUT"])
def update(id):
    """Update an existing debito record."""
    try:
        data = request.get_json()
        result = update_debito(id, data)
        if "error" in result:
            return jsonify({"success": False, "error": result["error"]}), 400
        return jsonify({"success": True, "data": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@debiti_bp.route("/<int:id>", methods=["DELETE"])
def delete(id):
    """Delete a debito record."""
    try:
        result = delete_debito(id)
        if "error" in result:
            return jsonify({"success": False, "error": result["error"]}), 400
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
