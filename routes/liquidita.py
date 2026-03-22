from flask import Blueprint, render_template, request, jsonify

from services.liquidita_service import (
    get_all_liquidita,
    create_liquidita,
    update_liquidita,
    delete_liquidita,
    get_liquidita_summary,
)

liquidita_bp = Blueprint("liquidita_bp", __name__, url_prefix="/piano-liquidita")


@liquidita_bp.route("/", methods=["GET"])
def index():
    """Render the piano liquidita page with all records and summary."""
    records_raw = get_all_liquidita()
    records = [dict(r) for r in records_raw] if records_raw and not isinstance(records_raw, dict) else []
    summary = get_liquidita_summary()
    return render_template(
        "piano_liquidita.html",
        records=records,
        summary=summary,
        active_page="piano_liquidita",
    )


@liquidita_bp.route("/", methods=["POST"])
def create():
    """Create a new liquidita record."""
    try:
        data = request.get_json()
        result = create_liquidita(data)
        if "error" in result:
            return jsonify({"success": False, "error": result["error"]}), 400
        return jsonify({"success": True, "data": result}), 201
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@liquidita_bp.route("/<int:id>", methods=["PUT"])
def update(id):
    """Update an existing liquidita record."""
    try:
        data = request.get_json()
        result = update_liquidita(id, data)
        if "error" in result:
            return jsonify({"success": False, "error": result["error"]}), 400
        return jsonify({"success": True, "data": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@liquidita_bp.route("/<int:id>", methods=["DELETE"])
def delete(id):
    """Delete a liquidita record."""
    try:
        result = delete_liquidita(id)
        if "error" in result:
            return jsonify({"success": False, "error": result["error"]}), 400
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
