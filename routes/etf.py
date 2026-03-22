from flask import Blueprint, render_template, request, jsonify

from services.etf_service import (
    get_all_etf,
    create_etf,
    update_etf,
    delete_etf,
    get_etf_riepilogo,
    get_etf_summary,
)

etf_bp = Blueprint("etf_bp", __name__, url_prefix="/etf")


@etf_bp.route("/", methods=["GET"])
def index():
    """Render the ETF page with all records, riepilogo, and summary."""
    records_raw = get_all_etf()
    records = [dict(r) for r in records_raw] if records_raw and not isinstance(records_raw, dict) else []
    riepilogo_raw = get_etf_riepilogo()
    riepilogo = [dict(r) for r in riepilogo_raw] if riepilogo_raw and not isinstance(riepilogo_raw, dict) else []
    summary = get_etf_summary()
    return render_template(
        "etf.html",
        records=records,
        riepilogo=riepilogo,
        summary=summary,
        active_page="etf",
    )


@etf_bp.route("/", methods=["POST"])
def create():
    """Create a new ETF record."""
    try:
        data = request.get_json()
        result = create_etf(data)
        if "error" in result:
            return jsonify({"success": False, "error": result["error"]}), 400
        return jsonify({"success": True, "data": result}), 201
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@etf_bp.route("/<int:id>", methods=["PUT"])
def update(id):
    """Update an existing ETF record."""
    try:
        data = request.get_json()
        result = update_etf(id, data)
        if "error" in result:
            return jsonify({"success": False, "error": result["error"]}), 400
        return jsonify({"success": True, "data": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@etf_bp.route("/<int:id>", methods=["DELETE"])
def delete(id):
    """Delete an ETF record."""
    try:
        result = delete_etf(id)
        if "error" in result:
            return jsonify({"success": False, "error": result["error"]}), 400
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
