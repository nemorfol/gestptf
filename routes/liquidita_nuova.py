from flask import Blueprint, render_template, request, jsonify

from services.liquidita_nuova_service import (
    get_all_liquidita_nuova,
    create_liquidita_nuova,
    update_liquidita_nuova,
    delete_liquidita_nuova,
    get_liquidita_summary_nuova,
    get_liquidita_storico,
)
from services.liquidita_service import (
    get_all_liquidita,
    create_liquidita,
    update_liquidita,
    delete_liquidita,
    get_liquidita_summary,
    generate_piano,
    clear_piano,
)

liquidita_nuova_bp = Blueprint("liquidita_nuova_bp", __name__, url_prefix="/liquidita")


@liquidita_nuova_bp.route("/", methods=["GET"])
def index():
    """Render the unified liquidita page with situazione + piano tabs."""
    # Situazione data
    records_raw = get_all_liquidita_nuova()
    records = [dict(r) for r in records_raw] if records_raw and not isinstance(records_raw, dict) else []
    summary = get_liquidita_summary_nuova()
    storico_raw = get_liquidita_storico()
    storico = storico_raw if isinstance(storico_raw, list) else []

    # Piano data
    piano_records_raw = get_all_liquidita()
    piano_records = piano_records_raw if isinstance(piano_records_raw, list) else []
    piano_summary = get_liquidita_summary()

    return render_template(
        "liquidita.html",
        records=records,
        summary=summary,
        storico=storico,
        piano_records=piano_records,
        piano_summary=piano_summary,
        active_page="liquidita_nuova",
    )


# ── Situazione CRUD ──

@liquidita_nuova_bp.route("/", methods=["POST"])
def create():
    """Create a new liquidita record (situazione)."""
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
    """Update an existing liquidita record (situazione)."""
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
    """Delete a liquidita record (situazione)."""
    try:
        data = request.get_json(silent=True) or {}
        # Check if this is a piano record deletion
        if data.get("tipo") == "piano":
            result = delete_liquidita(id)
        else:
            result = delete_liquidita_nuova(id)
        if "error" in result:
            return jsonify({"success": False, "error": result["error"]}), 400
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ── Piano CRUD ──

@liquidita_nuova_bp.route("/piano", methods=["POST"])
def piano_create():
    """Create a new piano record."""
    try:
        data = request.get_json()
        result = create_liquidita(data)
        if "error" in result:
            return jsonify({"success": False, "error": result["error"]}), 400
        return jsonify({"success": True, "data": result}), 201
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@liquidita_nuova_bp.route("/piano/<int:id>", methods=["PUT"])
def piano_update(id):
    """Update an existing piano record."""
    try:
        data = request.get_json()
        result = update_liquidita(id, data)
        if "error" in result:
            return jsonify({"success": False, "error": result["error"]}), 400
        return jsonify({"success": True, "data": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@liquidita_nuova_bp.route("/piano/<int:id>", methods=["DELETE"])
def piano_delete(id):
    """Delete a piano record."""
    try:
        result = delete_liquidita(id)
        if "error" in result:
            return jsonify({"success": False, "error": result["error"]}), 400
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@liquidita_nuova_bp.route("/genera-piano", methods=["POST"])
def genera_piano():
    """Generate a savings plan projection."""
    try:
        data = request.get_json()
        importo = float(data.get("importo_mensile", 0))
        pct_bsf = float(data.get("pct_bsf", 0))
        pct_bfpi = float(data.get("pct_bfpi", 0))
        pct_cd = float(data.get("pct_cd", 0))
        pct_altro = float(data.get("pct_altro", 0))
        data_inizio = data.get("data_inizio", "")
        num_mesi = int(data.get("num_mesi", 12))

        if importo <= 0:
            return jsonify({"success": False, "error": "Importo mensile deve essere > 0"}), 400
        if not data_inizio:
            return jsonify({"success": False, "error": "Data inizio obbligatoria"}), 400

        total_pct = pct_bsf + pct_bfpi + pct_cd + pct_altro
        if abs(total_pct - 100) > 0.01:
            return jsonify({"success": False, "error": f"Le percentuali devono sommare a 100% (attuale: {total_pct:.1f}%)"}), 400

        result = generate_piano(importo, pct_bsf, pct_bfpi, pct_cd, pct_altro,
                                data_inizio, num_mesi)
        if "error" in result:
            return jsonify({"success": False, "error": result["error"]}), 400
        return jsonify({"success": True, "data": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@liquidita_nuova_bp.route("/cancella-piano", methods=["POST"])
def cancella_piano():
    """Clear all piano records."""
    try:
        result = clear_piano()
        if "error" in result:
            return jsonify({"success": False, "error": result["error"]}), 400
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
