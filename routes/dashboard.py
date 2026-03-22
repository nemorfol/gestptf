from flask import Blueprint, render_template

from services.simulatore_service import get_parametro
from services.patrimonio_service import (
    get_all_patrimonio,
    get_latest_patrimonio,
    get_patrimonio_totali,
    get_patrimonio_percentuali,
)
from services.etf_service import get_etf_summary
from services.bond_service import get_bond_summary

dashboard_bp = Blueprint("dashboard_bp", __name__, url_prefix="/")


@dashboard_bp.route("/", methods=["GET"])
def index():
    """Render the main dashboard page."""
    latest = get_latest_patrimonio()
    totali = {}
    percentuali = {}

    if isinstance(latest, dict) and "error" not in latest:
        totali = get_patrimonio_totali(latest)
        percentuali = get_patrimonio_percentuali(latest)

    etf_summary = get_etf_summary()
    bond_summary = get_bond_summary()

    # Patrimonio history for charts
    patrimonio_history = get_all_patrimonio()
    if isinstance(patrimonio_history, dict) and "error" in patrimonio_history:
        patrimonio_history = []

    # Enrich history records with totals + raw asset values for interactive charts
    history_data = []
    asset_keys = ['immobili_esteri', 'immobile_italia', 'fondo_pensione', 'etf', 'bfp', 'btp', 'cash', 'cd', 'tfr_netto', 'debiti']
    for record in patrimonio_history:
        t = get_patrimonio_totali(record)
        if isinstance(t, dict) and "error" not in t:
            entry = {
                "data": record.get("data", ""),
                "totale": t["totale"],
                "totale_netto": t["totale_netto"],
                "totale_adj": t["totale_adj"],
            }
            for k in asset_keys:
                entry[k] = float(record.get(k, 0) or 0)
            history_data.append(entry)

    # Dashboard saved discount settings
    sconto_esteri = int(get_parametro("dashboard_sconto_esteri", "20") or 20)
    sconto_italia = int(get_parametro("dashboard_sconto_italia", "20") or 20)

    return render_template(
        "dashboard.html",
        latest=latest,
        totali=totali,
        percentuali=percentuali,
        etf_summary=etf_summary,
        bond_summary=bond_summary,
        patrimonio_history=history_data,
        sconto_esteri=sconto_esteri,
        sconto_italia=sconto_italia,
        active_page="dashboard",
    )
