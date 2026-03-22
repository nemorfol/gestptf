from flask import Blueprint, render_template, request, jsonify

from services.immobili_service import (
    get_all_immobili,
    create_immobile,
    update_immobile,
    delete_immobile,
    get_immobili_summary,
    add_valutazione,
    get_storico_immobile,
    get_all_storico,
)

immobili_bp = Blueprint("immobili_bp", __name__, url_prefix="/immobili")


@immobili_bp.route("/", methods=["GET"])
def index():
    """Render the immobili page with all records and summary."""
    records_raw = get_all_immobili()
    records = [dict(r) for r in records_raw] if records_raw and not isinstance(records_raw, dict) else []
    summary = get_immobili_summary()
    storico_raw = get_all_storico()
    storico = storico_raw if isinstance(storico_raw, list) else []
    return render_template(
        "immobili.html",
        records=records,
        summary=summary,
        storico=storico,
        active_page="immobili",
    )


@immobili_bp.route("/", methods=["POST"])
def create():
    """Create a new immobile record."""
    try:
        data = request.get_json()
        result = create_immobile(data)
        if "error" in result:
            return jsonify({"success": False, "error": result["error"]}), 400
        return jsonify({"success": True, "data": result}), 201
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@immobili_bp.route("/<int:id>", methods=["PUT"])
def update(id):
    """Update an existing immobile record."""
    try:
        data = request.get_json()
        result = update_immobile(id, data)
        if "error" in result:
            return jsonify({"success": False, "error": result["error"]}), 400
        return jsonify({"success": True, "data": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@immobili_bp.route("/<int:id>", methods=["DELETE"])
def delete(id):
    """Delete an immobile record."""
    try:
        result = delete_immobile(id)
        if "error" in result:
            return jsonify({"success": False, "error": result["error"]}), 400
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@immobili_bp.route("/<int:id>/valutazione", methods=["POST"])
def valutazione(id):
    """Add a new valuation for an immobile."""
    try:
        data = request.get_json()
        result = add_valutazione(id, data)
        if "error" in result:
            return jsonify({"success": False, "error": result["error"]}), 400
        return jsonify({"success": True, "data": result}), 201
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@immobili_bp.route("/<int:id>/storico", methods=["GET"])
def storico(id):
    """Return storico valutazioni as JSON."""
    try:
        records_raw = get_storico_immobile(id)
        records = [dict(r) for r in records_raw] if records_raw and not isinstance(records_raw, dict) else []
        return jsonify({"success": True, "data": records})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
