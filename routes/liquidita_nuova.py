from flask import Blueprint, render_template, request, jsonify

from services.liquidita_nuova_service import (
    get_all_liquidita_nuova,
    create_liquidita_nuova,
    update_liquidita_nuova,
    delete_liquidita_nuova,
    get_liquidita_summary_nuova,
    get_liquidita_storico,
)

liquidita_nuova_bp = Blueprint("liquidita_nuova_bp", __name__, url_prefix="/liquidita")


@liquidita_nuova_bp.route("/", methods=["GET"])
def index():
    """Render the liquidita page with all records and summary."""
    records_raw = get_all_liquidita_nuova()
    records = [dict(r) for r in records_raw] if records_raw and not isinstance(records_raw, dict) else []
    summary = get_liquidita_summary_nuova()
    storico_raw = get_liquidita_storico()
    storico = storico_raw if isinstance(storico_raw, list) else []
    return render_template(
        "liquidita_nuova.html",
        records=records,
        summary=summary,
        storico=storico,
        active_page="liquidita_nuova",
    )


@liquidita_nuova_bp.route("/", methods=["POST"])
def create():
    """Create a new liquidita record."""
    try:
        data = request.get_json()
        result = create_liquidita_nuova(data)
        if "error" in result:
            return jsonify({"success": False, "error": result["error"]}), 400
        return jsonify({"success": True, "data": result}), 201
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@liquidita_nuova_bp.route("/<int:id>", methods=["PUT"])
def update(id):
    """Update an existing liquidita record."""
    try:
        data = request.get_json()
        result = update_liquidita_nuova(id, data)
        if "error" in result:
            return jsonify({"success": False, "error": result["error"]}), 400
        return jsonify({"success": True, "data": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@liquidita_nuova_bp.route("/<int:id>", methods=["DELETE"])
def delete(id):
    """Delete a liquidita record."""
    try:
        result = delete_liquidita_nuova(id)
        if "error" in result:
            return jsonify({"success": False, "error": result["error"]}), 400
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
