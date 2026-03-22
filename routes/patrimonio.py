from flask import Blueprint, render_template, request, jsonify

from services.patrimonio_service import (
    get_all_patrimonio,
    get_latest_patrimonio,
    create_patrimonio,
    update_patrimonio,
    delete_patrimonio,
    get_patrimonio_totali,
    get_patrimonio_percentuali,
    get_patrimonio_variazioni,
)
from services.simulatore_service import calcola_impatto_vrp_patrimonio, get_parametro
from services.bfp_service import get_bfp_summary
from services.bfp_calculator import calcola_tutti_bfp
from services.fp_service import get_latest_fp
from services.tfr_service import get_latest_tfr

patrimonio_bp = Blueprint("patrimonio_bp", __name__, url_prefix="/patrimonio")


@patrimonio_bp.route("/", methods=["GET"])
def index():
    """Render the patrimonio page with all records enriched with totals and percentages."""
    records = get_all_patrimonio()
    variazioni = get_patrimonio_variazioni()

    # Enrich each record with computed totals and percentages
    enriched = []
    if isinstance(records, list):
        for record in records:
            totali = get_patrimonio_totali(record)
            percentuali = get_patrimonio_percentuali(record)
            record["totali"] = totali if isinstance(totali, dict) and "error" not in totali else {}
            record["percentuali"] = percentuali if isinstance(percentuali, dict) and "error" not in percentuali else {}
            enriched.append(record)

    return render_template(
        "patrimonio.html",
        records=enriched,
        variazioni=variazioni,
        active_page="patrimonio",
    )


@patrimonio_bp.route("/", methods=["POST"])
def create():
    """Create a new patrimonio record."""
    try:
        data = request.get_json()
        result = create_patrimonio(data)
        if "error" in result:
            return jsonify({"success": False, "error": result["error"]}), 400
        return jsonify({"success": True, "data": result}), 201
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@patrimonio_bp.route("/<int:id>", methods=["PUT"])
def update(id):
    """Update an existing patrimonio record."""
    try:
        data = request.get_json()
        result = update_patrimonio(id, data)
        if "error" in result:
            return jsonify({"success": False, "error": result["error"]}), 400
        return jsonify({"success": True, "data": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@patrimonio_bp.route("/valori-live", methods=["GET"])
def valori_live():
    """Get live values from linked sections (BFP, FP, TFR, etc.).

    BFP values are recalculated and filtered by subscription date.
    Accepts ?data=YYYY-MM-DD to filter BFP by subscription date.
    """
    try:
        from database import get_db as get_database

        data_ref = request.args.get("data", None)

        # Recalculate all BFP values to today's date
        calcola_tutti_bfp()

        # Sum BFP rimborso netto only for those subscribed on or before data_ref
        db = get_database()
        if data_ref:
            row = db.execute(
                "SELECT COALESCE(SUM(valore_rimborso_netto), 0) as totale FROM bfp WHERE data_sottoscrizione <= ?",
                (data_ref,),
            ).fetchone()
        else:
            row = db.execute(
                "SELECT COALESCE(SUM(valore_rimborso_netto), 0) as totale FROM bfp"
            ).fetchone()
        bfp_val = row["totale"] if row else 0

        # Latest Fondo Pensione (from dedicated table, fallback to patrimonio)
        fp = get_latest_fp()
        fp_val = fp.get("valore", 0) if isinstance(fp, dict) and "error" not in fp else 0
        if not fp_val:
            row = db.execute(
                "SELECT fondo_pensione FROM patrimonio WHERE fondo_pensione > 0 ORDER BY data DESC LIMIT 1"
            ).fetchone()
            fp_val = row[0] if row else 0

        # Latest TFR (from dedicated table, fallback to patrimonio)
        tfr = get_latest_tfr()
        tfr_val = tfr.get("valore_netto", 0) if isinstance(tfr, dict) and "error" not in tfr else 0
        if not tfr_val:
            row = db.execute(
                "SELECT tfr_netto FROM patrimonio WHERE tfr_netto > 0 ORDER BY data DESC LIMIT 1"
            ).fetchone()
            tfr_val = row[0] if row else 0

        db.close()

        # Fineco values (ETF, BTP, CD/XEON)
        fineco_etf = get_parametro("fineco_etf")
        fineco_btp = get_parametro("fineco_btp")
        fineco_cd = get_parametro("fineco_cd")

        result_data = {
            "bfp": round(bfp_val or 0, 2),
            "fondo_pensione": round(fp_val or 0, 2),
            "tfr_netto": round(tfr_val or 0, 2),
        }

        # Include Fineco values if available
        if fineco_etf is not None:
            result_data["etf"] = round(float(fineco_etf), 2)
        if fineco_btp is not None:
            result_data["btp"] = round(float(fineco_btp), 2)
        if fineco_cd is not None:
            result_data["cd"] = round(float(fineco_cd), 2)

        return jsonify({"success": True, "data": result_data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@patrimonio_bp.route("/vrp-impatto", methods=["POST"])
def vrp_impatto():
    """Calculate VRP impact on patrimonio for a given date."""
    try:
        data = request.get_json()
        data_target = data.get("data")
        if not data_target:
            return jsonify({"success": False, "error": "Data mancante"}), 400
        result = calcola_impatto_vrp_patrimonio(data_target)
        if isinstance(result, dict) and "error" in result:
            return jsonify({"success": False, "error": result["error"]}), 400
        return jsonify({"success": True, "data": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@patrimonio_bp.route("/<int:id>", methods=["DELETE"])
def delete(id):
    """Delete a patrimonio record."""
    try:
        result = delete_patrimonio(id)
        if "error" in result:
            return jsonify({"success": False, "error": result["error"]}), 400
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
