import os

from flask import Blueprint, render_template, request, jsonify, send_file

from werkzeug.utils import secure_filename
from config import EXCEL_PATH, UPLOAD_FOLDER, EXPORT_FOLDER
from services.fineco_import_service import parse_fineco_xls, import_fineco_to_db
from services.import_service import (
    import_from_excel,
    import_from_csv,
    export_to_csv,
    export_to_excel,
    export_to_excel_with_charts,
    SHEET_TABLE_MAP,
)

import_export_bp = Blueprint(
    "import_export_bp", __name__, url_prefix="/import-export"
)

# All exportable table names
ALL_TABLES = list(SHEET_TABLE_MAP.values())


@import_export_bp.route("/", methods=["GET"])
def index():
    """Render the import/export page."""
    return render_template(
        "import_export.html",
        active_page="import_export",
    )


@import_export_bp.route("/importa-excel-base", methods=["POST"])
def importa_excel_base():
    """Import data from the original Excel file configured in EXCEL_PATH."""
    try:
        result = import_from_excel(EXCEL_PATH)
        if "error" in result:
            return jsonify({"success": False, "error": result["error"]}), 400
        return jsonify({"success": True, "data": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@import_export_bp.route("/importa-excel", methods=["POST"])
def importa_excel():
    """Import data from an uploaded Excel file."""
    try:
        if "file" not in request.files:
            return jsonify({"success": False, "error": "Nessun file caricato"}), 400

        file = request.files["file"]
        if file.filename == "":
            return jsonify({"success": False, "error": "Nessun file selezionato"}), 400

        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        filepath = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(filepath)

        result = import_from_excel(filepath)
        if "error" in result:
            return jsonify({"success": False, "error": result["error"]}), 400
        return jsonify({"success": True, "data": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@import_export_bp.route("/importa-csv", methods=["POST"])
def importa_csv():
    """Import data from an uploaded CSV file for a specified table."""
    try:
        if "file" not in request.files:
            return jsonify({"success": False, "error": "Nessun file caricato"}), 400

        file = request.files["file"]
        table_name = request.form.get("table_name", "")

        if file.filename == "":
            return jsonify({"success": False, "error": "Nessun file selezionato"}), 400
        if not table_name:
            return jsonify({"success": False, "error": "Tabella non specificata"}), 400

        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        filepath = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(filepath)

        result = import_from_csv(table_name, filepath)
        if "error" in result:
            return jsonify({"success": False, "error": result["error"]}), 400
        return jsonify({"success": True, "data": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@import_export_bp.route("/importa-fineco", methods=["POST"])
def importa_fineco():
    """Import from Fineco portfolio export .xls file.

    Parses the file, optionally updates ETF/Bond positions,
    and returns patrimonio values (ETF, BTP, CD/XEON).
    """
    try:
        if "file" not in request.files:
            return jsonify({"success": False, "error": "Nessun file caricato"}), 400

        file = request.files["file"]
        if file.filename == "":
            return jsonify({"success": False, "error": "Nessun file selezionato"}), 400

        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)

        # Parse
        parsed = parse_fineco_xls(filepath)
        if "error" in parsed:
            return jsonify({"success": False, "error": parsed["error"]}), 400

        # Import
        data_import = request.form.get("data", None)
        update_positions = request.form.get("update_positions", "1") == "1"
        result = import_fineco_to_db(parsed, data_import, update_positions)

        if "error" in result:
            return jsonify({"success": False, "error": result["error"]}), 400

        return jsonify({
            "success": True,
            "data": {
                "parsed": {
                    "etf": parsed["etf"],
                    "bond": parsed["bond"],
                    "totale_etf": parsed["totale_etf"],
                    "totale_btp": parsed["totale_btp"],
                    "totale_cash_xeon": parsed["totale_cash_xeon"],
                    "totale_portafoglio": parsed["totale_portafoglio"],
                    "errors": parsed["errors"],
                },
                "import_result": result,
            },
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@import_export_bp.route("/importa-fineco-preview", methods=["POST"])
def importa_fineco_preview():
    """Preview Fineco import without saving to DB."""
    try:
        if "file" not in request.files:
            return jsonify({"success": False, "error": "Nessun file caricato"}), 400

        file = request.files["file"]
        if file.filename == "":
            return jsonify({"success": False, "error": "Nessun file selezionato"}), 400

        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)

        parsed = parse_fineco_xls(filepath)
        if "error" in parsed:
            return jsonify({"success": False, "error": parsed["error"]}), 400

        return jsonify({"success": True, "data": parsed})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@import_export_bp.route("/esporta-csv/<table_name>", methods=["GET"])
def esporta_csv(table_name):
    """Export a single table as a CSV file download."""
    try:
        os.makedirs(EXPORT_FOLDER, exist_ok=True)
        filepath = os.path.join(EXPORT_FOLDER, f"{table_name}.csv")

        result = export_to_csv(table_name, filepath)
        if "error" in result:
            return jsonify({"success": False, "error": result["error"]}), 400

        return send_file(
            filepath,
            mimetype="text/csv",
            as_attachment=True,
            download_name=f"{table_name}.csv",
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@import_export_bp.route("/esporta-excel", methods=["GET"])
def esporta_excel():
    """Export all tables as an Excel file download."""
    try:
        os.makedirs(EXPORT_FOLDER, exist_ok=True)
        filepath = os.path.join(EXPORT_FOLDER, "gestptf_export.xlsx")

        result = export_to_excel(ALL_TABLES, filepath)
        if "error" in result:
            return jsonify({"success": False, "error": result["error"]}), 400

        return send_file(
            filepath,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name="gestptf_export.xlsx",
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@import_export_bp.route("/esporta-excel-grafici", methods=["GET"])
def esporta_excel_grafici():
    """Export patrimonio data with charts as an Excel file download."""
    try:
        os.makedirs(EXPORT_FOLDER, exist_ok=True)
        filepath = os.path.join(EXPORT_FOLDER, "gestptf_grafici.xlsx")

        result = export_to_excel_with_charts(filepath)
        if "error" in result:
            return jsonify({"success": False, "error": result["error"]}), 400

        return send_file(
            filepath,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name="gestptf_grafici.xlsx",
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
