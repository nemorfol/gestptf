from flask import Blueprint, render_template, request, jsonify

from services.simulatore_service import (
    simula_bsf_vs_bfp,
    simula_btpi,
    calcola_rata_mensile_btpi,
    simula_vendita_riserva,
    get_all_vrp,
    get_vrp_by_id,
    save_vrp,
    delete_vrp,
    get_parametri_simulazione,
    save_parametri_simulazione,
)
from services.immobili_service import get_all_immobili

simulatore_bp = Blueprint("simulatore_bp", __name__, url_prefix="/simulatore")


@simulatore_bp.route("/bsf", methods=["GET"])
def bsf_page():
    """Render the BSF simulator page with default parameters from DB."""
    parametri = get_parametri_simulazione()
    if isinstance(parametri, dict) and "error" in parametri:
        parametri = {}
    return render_template(
        "simulatore_bsf.html",
        parametri=parametri,
        active_page="simulatore_bsf",
    )


@simulatore_bp.route("/bsf/calcola", methods=["POST"])
def bsf_calcola():
    """Run BSF vs BFP simulation with posted parameters."""
    try:
        data = request.get_json()
        importo = data.get("importo", 1000)
        tasso_bsf = data.get("tasso_bsf", 3.0)
        tasso_bfp_ord = data.get("tasso_bfp_ord", 2.5)
        anni = data.get("anni", 22)

        risultati = simula_bsf_vs_bfp(importo, tasso_bsf, tasso_bfp_ord, anni)
        if isinstance(risultati, dict) and "error" in risultati:
            return jsonify({"success": False, "error": risultati["error"]}), 400
        return jsonify({"success": True, "data": risultati})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@simulatore_bp.route("/btpi", methods=["GET"])
def btpi_page():
    """Render the BTPi simulator page with default parameters."""
    parametri = get_parametri_simulazione()
    if isinstance(parametri, dict) and "error" in parametri:
        parametri = {}
    return render_template(
        "simulatore_btpi.html",
        parametri=parametri,
        active_page="simulatore_btpi",
    )


@simulatore_bp.route("/btpi/calcola", methods=["POST"])
def btpi_calcola():
    """Run BTPi simulation and calculate monthly income."""
    try:
        data = request.get_json()

        valore_nominale = data.get("valore_nominale", 0)
        quotazione = data.get("quotazione", 100)
        coeff_indicizz = data.get("coeff_indicizz", 1.0)
        inflazione_prevista = data.get("inflazione_prevista", 1.4)
        anno_rimborso = data.get("anno_rimborso", 2040)
        anno_corrente = data.get("anno_corrente", 2025)

        risultati_btpi = simula_btpi(
            valore_nominale, quotazione, coeff_indicizz,
            inflazione_prevista, anno_rimborso, anno_corrente,
        )
        if isinstance(risultati_btpi, dict) and "error" in risultati_btpi:
            return jsonify({"success": False, "error": risultati_btpi["error"]}), 400

        # Calculate monthly income if requested
        rata = None
        if data.get("importo_netto") and data.get("speranza_vita_anni"):
            rata = calcola_rata_mensile_btpi(
                data["importo_netto"], data["speranza_vita_anni"]
            )
            if isinstance(rata, dict) and "error" in rata:
                rata = None

        return jsonify({
            "success": True,
            "data": risultati_btpi,
            "rata_mensile": rata,
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@simulatore_bp.route("/vrp", methods=["GET"])
def vrp_page():
    """Render the VRP (Vendita con Riserva di Proprietà) simulator page."""
    parametri = get_parametri_simulazione()
    if isinstance(parametri, dict) and "error" in parametri:
        parametri = {}
    immobili_raw = get_all_immobili()
    immobili = immobili_raw if isinstance(immobili_raw, list) else []
    saved = get_all_vrp()
    saved_list = saved if isinstance(saved, list) else []
    return render_template(
        "simulatore_vrp.html",
        parametri=parametri,
        immobili=immobili,
        saved_list=saved_list,
        active_page="simulatore_vrp",
    )


@simulatore_bp.route("/vrp/calcola", methods=["POST"])
def vrp_calcola():
    """Run VRP simulation with posted parameters."""
    try:
        data = request.get_json()
        risultati = simula_vendita_riserva(data)
        if isinstance(risultati, dict) and "error" in risultati:
            return jsonify({"success": False, "error": risultati["error"]}), 400
        return jsonify({"success": True, "data": risultati})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@simulatore_bp.route("/vrp/salva", methods=["POST"])
def vrp_salva():
    """Save a VRP simulation to the database."""
    try:
        data = request.get_json()
        result = save_vrp(data)
        if "error" in result:
            return jsonify({"success": False, "error": result["error"]}), 400
        return jsonify({"success": True, "data": result}), 201
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@simulatore_bp.route("/vrp/<int:id>", methods=["GET"])
def vrp_get(id):
    """Get a saved VRP simulation by id."""
    try:
        result = get_vrp_by_id(id)
        if isinstance(result, dict) and "error" in result:
            return jsonify({"success": False, "error": result["error"]}), 404
        return jsonify({"success": True, "data": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@simulatore_bp.route("/vrp/<int:id>", methods=["DELETE"])
def vrp_delete(id):
    """Delete a saved VRP simulation."""
    try:
        result = delete_vrp(id)
        if "error" in result:
            return jsonify({"success": False, "error": result["error"]}), 400
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@simulatore_bp.route("/parametri", methods=["POST"])
def salva_parametri():
    """Save simulation parameters to DB."""
    try:
        data = request.get_json()
        result = save_parametri_simulazione(data)
        if "error" in result:
            return jsonify({"success": False, "error": result["error"]}), 400
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
