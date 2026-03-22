from flask import Blueprint, render_template, request, jsonify

from database import get_db

impostazioni_bp = Blueprint("impostazioni_bp", __name__, url_prefix="/impostazioni")


@impostazioni_bp.route("/addizionali/regioni", methods=["GET"])
def addizionali_regioni():
    """Return list of distinct regions."""
    try:
        db = get_db()
        rows = db.execute(
            "SELECT DISTINCT nome FROM addizionali_irpef WHERE tipo = 'regionale' ORDER BY nome"
        ).fetchall()
        db.close()
        return jsonify({"success": True, "data": [r[0] for r in rows]})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@impostazioni_bp.route("/addizionali/comuni", methods=["GET"])
def addizionali_comuni():
    """Return list of comuni, optionally filtered by region."""
    try:
        regione = request.args.get("regione", "")
        db = get_db()
        if regione:
            rows = db.execute(
                "SELECT DISTINCT nome, aliquota FROM addizionali_irpef WHERE tipo = 'comunale' AND regione = ? ORDER BY nome",
                (regione,),
            ).fetchall()
        else:
            rows = db.execute(
                "SELECT DISTINCT nome, aliquota, regione FROM addizionali_irpef WHERE tipo = 'comunale' ORDER BY nome"
            ).fetchall()
        db.close()
        return jsonify({"success": True, "data": [dict(r) for r in rows]})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@impostazioni_bp.route("/addizionali/calcola", methods=["POST"])
def addizionali_calcola():
    """Calculate addizionale regionale for a given region and income."""
    try:
        data = request.get_json()
        regione = data.get("regione", "")
        reddito = float(data.get("reddito", 0))

        db = get_db()
        rows = db.execute(
            """SELECT reddito_da, reddito_a, aliquota FROM addizionali_irpef
               WHERE tipo = 'regionale' AND nome = ?
               ORDER BY reddito_da""",
            (regione,),
        ).fetchall()
        db.close()

        if not rows:
            return jsonify({"success": True, "data": {"aliquota": 0, "found": False}})

        # Find matching bracket
        aliquota = 0
        for r in rows:
            if reddito > r["reddito_da"] and reddito <= r["reddito_a"]:
                aliquota = r["aliquota"]
                break
        # If no bracket matched, use last one
        if aliquota == 0 and rows:
            aliquota = rows[-1]["aliquota"]

        return jsonify({"success": True, "data": {
            "aliquota": aliquota,
            "found": True,
            "scaglioni": [dict(r) for r in rows],
        }})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


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
