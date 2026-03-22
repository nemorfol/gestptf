from flask import Blueprint, render_template, request, jsonify

from services.bond_service import (
    get_all_bond,
    create_bond,
    update_bond,
    delete_bond,
    get_bond_riepilogo,
    get_bond_summary,
)

bond_bp = Blueprint("bond_bp", __name__, url_prefix="/bond")


@bond_bp.route("/", methods=["GET"])
def index():
    """Render the bond page with all records, riepilogo, and summary."""
    records_raw = get_all_bond()
    records = [dict(r) for r in records_raw] if records_raw and not isinstance(records_raw, dict) else []
    riepilogo_raw = get_bond_riepilogo()
    riepilogo = [dict(r) for r in riepilogo_raw] if riepilogo_raw and not isinstance(riepilogo_raw, dict) else []
    summary = get_bond_summary()
    return render_template(
        "bond.html",
        records=records,
        riepilogo=riepilogo,
        summary=summary,
        active_page="bond",
    )


@bond_bp.route("/", methods=["POST"])
def create():
    """Create a new bond record."""
    try:
        data = request.get_json()
        result = create_bond(data)
        if "error" in result:
            return jsonify({"success": False, "error": result["error"]}), 400
        return jsonify({"success": True, "data": result}), 201
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bond_bp.route("/<int:id>", methods=["PUT"])
def update(id):
    """Update an existing bond record."""
    try:
        data = request.get_json()
        result = update_bond(id, data)
        if "error" in result:
            return jsonify({"success": False, "error": result["error"]}), 400
        return jsonify({"success": True, "data": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bond_bp.route("/<int:id>", methods=["DELETE"])
def delete(id):
    """Delete a bond record."""
    try:
        result = delete_bond(id)
        if "error" in result:
            return jsonify({"success": False, "error": result["error"]}), 400
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
