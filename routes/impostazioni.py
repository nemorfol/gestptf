from flask import Blueprint, render_template, request, jsonify

from database import get_db

impostazioni_bp = Blueprint("impostazioni_bp", __name__, url_prefix="/impostazioni")


@impostazioni_bp.route("/", methods=["GET"])
def index():
    """Render the settings page."""
    try:
        db = get_db()
        rows = db.execute(
            "SELECT chiave, valore, descrizione, categoria FROM parametri ORDER BY categoria, chiave"
        ).fetchall()
        db.close()
        parametri = [dict(r) for r in rows]
    except Exception:
        parametri = []

    return render_template(
        "impostazioni.html",
        parametri=parametri,
        active_page="impostazioni",
    )


@impostazioni_bp.route("/salva", methods=["POST"])
def salva():
    """Save updated parameters."""
    try:
        data = request.get_json()
        db = get_db()
        for chiave, valore in data.items():
            db.execute(
                "UPDATE parametri SET valore = ? WHERE chiave = ?",
                (str(valore), chiave),
            )
        db.commit()
        db.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
