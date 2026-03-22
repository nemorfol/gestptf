from flask import Blueprint, render_template, request, jsonify

from services.patrimonio_service import get_latest_patrimonio
from services.simulatore_service import simula_sostenibilita

simulazione_inv_bp = Blueprint(
    "simulazione_inv_bp", __name__, url_prefix="/simulazione-investimento"
)


@simulazione_inv_bp.route("/", methods=["GET"])
def index():
    """Render the simulazione investimento page with latest patrimonio."""
    latest_patrimonio = get_latest_patrimonio()
    if isinstance(latest_patrimonio, dict) and "error" in latest_patrimonio:
        latest_patrimonio = {}

    return render_template(
        "simulazione_investimento.html",
        latest_patrimonio=latest_patrimonio,
        active_page="simulazione_inv",
    )


@simulazione_inv_bp.route("/calcola", methods=["POST"])
def calcola():
    """Run sustainability simulation."""
    try:
        data = request.get_json()
        risultati = simula_sostenibilita(data)
        if isinstance(risultati, dict) and "error" in risultati:
            return jsonify({"success": False, "error": risultati["error"]}), 400
        return jsonify({"success": True, "data": risultati})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
