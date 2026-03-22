import os
from flask import Blueprint, render_template, request, jsonify
from werkzeug.utils import secure_filename

from services.bfp_service import (
    get_all_bfp,
    get_bfp_by_id,
    create_bfp,
    update_bfp,
    delete_bfp,
    get_bfp_riepilogo,
    get_bfp_summary,
    import_bfp_from_excel,
)
from services.bfp_pdf_parser import import_all_bfp_pdfs, get_coefficienti_serie
from services.bfp_calculator import calcola_tutti_bfp, calcola_bollo, get_piano_rimborso, calcola_rendita
from config import UPLOAD_FOLDER, BASE_DIR

bfp_bp = Blueprint("bfp_bp", __name__, url_prefix="/bfp")


@bfp_bp.route("/", methods=["GET"])
def index():
    """Render the BFP page with all records, riepilogo, and summary."""
    # Recalculate all BFP values to today before displaying
    calcola_tutti_bfp()
    records_raw = get_all_bfp()
    records = [dict(r) for r in records_raw] if records_raw and not isinstance(records_raw, dict) else []
    # Calculate bollo for each BFP
    totale_lordo = sum(float(r.get("valore_lordo_attuale", 0) or 0) for r in records)
    for r in records:
        val_lordo = float(r.get("valore_lordo_attuale", 0) or 0)
        r["bollo_annuo"] = calcola_bollo(val_lordo, totale_lordo)
    riepilogo_raw = get_bfp_riepilogo()
    riepilogo = [dict(r) for r in riepilogo_raw] if riepilogo_raw and not isinstance(riepilogo_raw, dict) else []
    summary = get_bfp_summary()
    # Add bollo info to summary
    summary["totale_bollo"] = sum(r["bollo_annuo"] for r in records)
    summary["esente_bollo"] = totale_lordo < 5000
    # Get which series have coefficients imported (for enabling/disabling Piano Rimborso)
    from database import get_db as _get_db
    _db = _get_db()
    _serie_rows = _db.execute("SELECT DISTINCT serie FROM bfp_coefficienti WHERE tipo_tabella='B'").fetchall()
    _db.close()
    serie_con_coefficienti = set(r[0] for r in _serie_rows)
    for r in records:
        r["has_coefficienti"] = (r.get("serie") or "").upper() in {s.upper() for s in serie_con_coefficienti}
    return render_template(
        "bfp.html",
        records=records,
        riepilogo=riepilogo,
        summary=summary,
        active_page="bfp",
    )


@bfp_bp.route("/", methods=["POST"])
def create():
    """Create a new BFP record."""
    try:
        data = request.get_json()
        result = create_bfp(data)
        if "error" in result:
            return jsonify({"success": False, "error": result["error"]}), 400
        return jsonify({"success": True, "data": result}), 201
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bfp_bp.route("/<int:id>", methods=["PUT"])
def update(id):
    """Update an existing BFP record."""
    try:
        data = request.get_json()
        result = update_bfp(id, data)
        if "error" in result:
            return jsonify({"success": False, "error": result["error"]}), 400
        return jsonify({"success": True, "data": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bfp_bp.route("/<int:id>", methods=["DELETE"])
def delete(id):
    """Delete a BFP record."""
    try:
        result = delete_bfp(id)
        if "error" in result:
            return jsonify({"success": False, "error": result["error"]}), 400
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bfp_bp.route("/importa-excel", methods=["POST"])
def importa_excel():
    """Handle uploaded RPOL Excel file for BFP import."""
    try:
        if "file" not in request.files:
            return jsonify({"success": False, "error": "Nessun file selezionato"}), 400
        file = request.files["file"]
        if file.filename == "":
            return jsonify({"success": False, "error": "Nessun file selezionato"}), 400

        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)

        result = import_bfp_from_excel(filepath)
        if "error" in result:
            return jsonify({"success": False, "error": result["error"]}), 400
        return jsonify({"success": True, "data": result}), 201
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bfp_bp.route("/importa-pdf", methods=["POST"])
def importa_pdf():
    """Import BFP coefficient tables from PDF fogli informativi."""
    try:
        pdf_dir = os.path.join(BASE_DIR, "pdf", "bfp")
        result = import_all_bfp_pdfs(pdf_dir)
        if "error" in result:
            return jsonify({"success": False, "error": result["error"]}), 400
        return jsonify({"success": True, "data": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bfp_bp.route("/ricalcola", methods=["POST"])
def ricalcola():
    """Recalculate all BFP values using imported coefficients."""
    try:
        result = calcola_tutti_bfp()
        if isinstance(result, dict) and "error" in result:
            return jsonify({"success": False, "error": result["error"]}), 400
        return jsonify({"success": True, "count": len(result), "data": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bfp_bp.route("/piano-rimborso/<int:id>", methods=["GET"])
def piano_rimborso(id):
    """Get amortization schedule for a specific BFP."""
    try:
        bfp = get_bfp_by_id(id)
        if isinstance(bfp, dict) and "error" in bfp:
            return jsonify({"success": False, "error": bfp["error"]}), 404

        serie = bfp.get("serie")
        valore_nominale = bfp.get("valore_nominale", 0)
        data_sottoscrizione = bfp.get("data_sottoscrizione")

        if not serie:
            return jsonify({"success": False, "error": "Serie non specificata per questo BFP"}), 400

        result = get_piano_rimborso(serie, valore_nominale, data_sottoscrizione)
        if "error" in result:
            return jsonify({"success": False, "error": result["error"]}), 400

        result["bfp"] = bfp
        return jsonify({"success": True, "data": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bfp_bp.route("/rendita-totale", methods=["GET"])
def rendita_totale():
    """Calculate aggregate rendita for ALL BSF/BO65 BFP given a birth date."""
    try:
        data_nascita = request.args.get("data_nascita")
        if not data_nascita:
            return jsonify({"success": False, "error": "Parametro 'data_nascita' obbligatorio"}), 400

        from datetime import datetime
        try:
            nascita = datetime.strptime(data_nascita, "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"success": False, "error": "Formato data non valido (YYYY-MM-DD)"}), 400

        records_raw = get_all_bfp()
        records = [dict(r) for r in records_raw] if records_raw and not isinstance(records_raw, dict) else []

        # Filter BSF and BO65 only
        rendita_buoni = []
        totale_mensile_lorda = 0
        totale_mensile_netta = 0
        totale_nominale_rendita = 0
        totale_valore_65 = 0

        for bfp in records:
            serie = (bfp.get("serie") or "").upper()
            if not (serie.startswith("BO165A") or serie.startswith("SF165A")):
                continue

            # Calculate age at subscription
            ds = bfp.get("data_sottoscrizione")
            if not ds:
                continue
            try:
                data_sott = datetime.strptime(str(ds)[:10], "%Y-%m-%d").date()
            except ValueError:
                continue

            diff_months = (data_sott.year - nascita.year) * 12 + (data_sott.month - nascita.month)
            if data_sott.day < nascita.day:
                diff_months -= 1
            anni = diff_months // 12
            mesi_resto = diff_months % 12
            eta = anni + 0.5 if mesi_resto >= 6 else float(anni)

            valore_nom = float(bfp.get("valore_nominale", 0) or 0)
            result = calcola_rendita(bfp.get("serie"), valore_nom, eta)

            if "error" in result:
                continue

            # Also get value at 65 (Tabella A)
            from services.bfp_calculator import calcola_valore_scadenza
            val_65 = calcola_valore_scadenza(bfp.get("serie"), valore_nom, ds)
            valore_al_65_netto = val_65.get("valore_netto", valore_nom) if "error" not in val_65 else valore_nom

            totale_mensile_lorda += result["rata_mensile_lorda"]
            totale_mensile_netta += result["rata_mensile_netta"]
            totale_nominale_rendita += valore_nom
            totale_valore_65 += valore_al_65_netto

            rendita_buoni.append({
                "id": bfp["id"],
                "tipologia": bfp.get("tipologia", ""),
                "serie": bfp.get("serie", ""),
                "valore_nominale": valore_nom,
                "data_sottoscrizione": str(ds),
                "eta_sottoscrizione": eta,
                "rata_mensile_netta": result["rata_mensile_netta"],
                "rata_mensile_lorda": result["rata_mensile_lorda"],
                "valore_al_65_netto": valore_al_65_netto,
            })

        return jsonify({
            "success": True,
            "data": {
                "totale_mensile_lorda": round(totale_mensile_lorda, 2),
                "totale_mensile_netta": round(totale_mensile_netta, 2),
                "totale_annua_lorda": round(totale_mensile_lorda * 12, 2),
                "totale_annua_netta": round(totale_mensile_netta * 12, 2),
                "totale_rendita_15_anni_lorda": round(totale_mensile_lorda * 180, 2),
                "totale_rendita_15_anni_netta": round(totale_mensile_netta * 180, 2),
                "totale_nominale": round(totale_nominale_rendita, 2),
                "totale_valore_65": round(totale_valore_65, 2),
                "num_buoni": len(rendita_buoni),
                "dettaglio": rendita_buoni,
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bfp_bp.route("/rendita/<int:id>", methods=["GET"])
def rendita(id):
    """Calculate rendita (monthly annuity 65-80) for a specific BSF/BO65 BFP."""
    try:
        bfp = get_bfp_by_id(id)
        if isinstance(bfp, dict) and "error" in bfp:
            return jsonify({"success": False, "error": bfp["error"]}), 404

        eta = request.args.get("eta")
        if not eta:
            return jsonify({"success": False, "error": "Parametro 'eta' (eta alla sottoscrizione) obbligatorio"}), 400

        try:
            eta = float(eta)
        except (ValueError, TypeError):
            return jsonify({"success": False, "error": "Parametro 'eta' deve essere un numero (es. 42 o 42.5)"}), 400

        serie = bfp.get("serie")
        valore_nominale = bfp.get("valore_nominale", 0)

        result = calcola_rendita(serie, valore_nominale, eta)
        if "error" in result:
            return jsonify({"success": False, "error": result["error"]}), 400

        result["bfp_id"] = id
        result["serie"] = serie
        result["valore_nominale"] = valore_nominale
        return jsonify({"success": True, "data": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bfp_bp.route("/coefficienti/<serie>", methods=["GET"])
def coefficienti(serie):
    """Return all coefficients for a given serie."""
    try:
        result = get_coefficienti_serie(serie)
        if isinstance(result, dict) and "error" in result:
            return jsonify({"success": False, "error": result["error"]}), 404
        return jsonify({"success": True, "data": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bfp_bp.route("/serie-disponibili", methods=["GET"])
def serie_disponibili():
    """Return all available BFP series (from coefficienti + existing BFP)."""
    try:
        from database import get_db
        db = get_db()
        rows = db.execute(
            """SELECT serie, tipologia FROM (
                   SELECT DISTINCT serie, UPPER(tipologia) as tipologia FROM bfp_coefficienti
                   UNION
                   SELECT DISTINCT serie, UPPER(tipologia) as tipologia FROM bfp
               ) GROUP BY serie
               ORDER BY tipologia, serie"""
        ).fetchall()
        db.close()
        return jsonify({
            "success": True,
            "data": [{"serie": r[0], "tipologia": r[1]} for r in rows],
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bfp_bp.route("/calcola-valori", methods=["POST"])
def calcola_valori():
    """Calculate current and maturity values for a BFP given serie, nominale, data.

    Also calculates rendita if the serie is BSF/BO65, using anno_nascita from parametri.
    """
    try:
        from services.bfp_calculator import calcola_valore_rimborso, calcola_valore_scadenza, _get_coefficiente_accumulo
        from services.simulatore_service import get_parametro
        from datetime import datetime

        data = request.get_json()
        serie = data.get("serie")
        valore_nominale = data.get("valore_nominale", 0)
        data_sottoscrizione = data.get("data_sottoscrizione")

        result = {"serie": serie, "valore_nominale": valore_nominale}

        rimborso = calcola_valore_rimborso(serie, valore_nominale, data_sottoscrizione)
        if isinstance(rimborso, dict) and "error" not in rimborso:
            result["valore_lordo_attuale"] = rimborso["valore_lordo"]
            result["ritenuta_fiscale"] = rimborso["ritenuta"]
            result["valore_rimborso_netto"] = rimborso["valore_netto"]

        scadenza = calcola_valore_scadenza(serie, valore_nominale, data_sottoscrizione)
        if isinstance(scadenza, dict) and "error" not in scadenza:
            result["valore_netto_scadenza"] = scadenza["valore_netto"]
            result["durata_anni"] = scadenza.get("anni_scadenza", 0)

        # Calculate rendita for BSF/BO65 using data_nascita
        serie_upper = (serie or "").upper()
        if serie_upper.startswith("BO165A") or serie_upper.startswith("SF165A"):
            data_nascita = get_parametro("data_nascita")
            if data_nascita and data_sottoscrizione:
                try:
                    from datetime import datetime as dt
                    dn = dt.strptime(data_nascita[:10], "%Y-%m-%d").date()
                    ds = dt.strptime(data_sottoscrizione[:10], "%Y-%m-%d").date()
                    # Age in complete years at subscription
                    eta_anni = ds.year - dn.year - (1 if (ds.month, ds.day) < (dn.month, dn.day) else 0)
                    # Check if 6+ months past birthday for half-year
                    compleanno_anno = ds.year if (ds.month, ds.day) >= (dn.month, dn.day) else ds.year - 1
                    compleanno = dn.replace(year=compleanno_anno)
                    mesi_dal_compleanno = (ds.year - compleanno.year) * 12 + (ds.month - compleanno.month)
                    if ds.day < compleanno.day:
                        mesi_dal_compleanno -= 1
                    eta_sott = eta_anni + (0.5 if mesi_dal_compleanno >= 6 else 0)

                    rendita = calcola_rendita(serie, valore_nominale, eta_sott)
                    if isinstance(rendita, dict) and "error" not in rendita:
                        result["rendita"] = rendita
                        result["eta_sottoscrizione"] = eta_sott
                        result["anno_inizio_rendita"] = dn.year + 65
                        result["anno_fine_rendita"] = dn.year + 80

                    # Valore rimborso al 65° anno from Tabella A
                    coeff_acc = _get_coefficiente_accumulo(serie, eta_sott)
                    if coeff_acc:
                        vn = float(valore_nominale)
                        result["valore_rimborso_65"] = round(vn * coeff_acc["coeff_netto"], 2)
                        result["valore_rimborso_65_lordo"] = round(vn * coeff_acc["coeff_lordo"], 2)
                        result["valore_netto_scadenza"] = result["valore_rimborso_65"]
                except (ValueError, TypeError):
                    pass

        return jsonify({"success": True, "data": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
