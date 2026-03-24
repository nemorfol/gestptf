"""BFP Excel export with multiple sheets and charts."""
import os
import xlsxwriter
from services.bfp_service import get_all_bfp, get_bfp_riepilogo, get_bfp_summary
from services.bfp_calculator import calcola_tutti_bfp, get_piano_rimborso, calcola_bollo


def export_bfp_excel(filepath, data_nascita=None):
    """Export comprehensive BFP data to Excel with charts.

    Sheets:
        1. Riepilogo - Summary totals + pie chart by tipologia
        2. Lista BFP - All BFP records with details
        3. Rendita 65-80 - BSF/BO65 rendita details (if data_nascita provided)
        4. One sheet per BFP with piano rimborso + chart
    """
    try:
        records_raw = get_all_bfp()
        if not records_raw or (isinstance(records_raw, dict) and "error" in records_raw):
            return {"error": "Nessun BFP presente"}

        records = [dict(r) for r in records_raw]

        # Calculate current values and bollo
        calc_result = calcola_tutti_bfp()
        calc_map = {}
        if isinstance(calc_result, list):
            for r in calc_result:
                calc_map[r["id"]] = r

        # Merge calculated fields into records
        for rec in records:
            calc = calc_map.get(rec["id"], {})
            for key in ["valore_lordo_attuale", "ritenuta_fiscale", "valore_rimborso_netto",
                        "valore_lordo_scadenza", "ritenuta_scadenza", "valore_netto_scadenza",
                        "bollo_annuo"]:
                if key in calc:
                    rec[key] = calc[key]

        riepilogo = get_bfp_riepilogo()
        summary = get_bfp_summary()

        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
        workbook = xlsxwriter.Workbook(filepath)

        # --- Formats ---
        bold_fmt = workbook.add_format({"bold": True, "bg_color": "#D9E1F2"})
        money_fmt = workbook.add_format({"num_format": "#,##0.00"})
        pct_fmt = workbook.add_format({"num_format": "0.0000"})
        date_fmt = workbook.add_format({"num_format": "yyyy-mm-dd"})
        header_green = workbook.add_format({"bold": True, "bg_color": "#C6EFCE"})
        header_warn = workbook.add_format({"bold": True, "bg_color": "#FCE4D6"})
        bold_money = workbook.add_format({"bold": True, "num_format": "#,##0.00"})

        # =============================================
        # SHEET 1: Riepilogo
        # =============================================
        ws_riep = workbook.add_worksheet("Riepilogo")

        # Summary totals
        ws_riep.write(0, 0, "Riepilogo BFP", workbook.add_format({"bold": True, "font_size": 14}))

        summary_labels = [
            ("Numero BFP", summary.get("totale_count", 0)),
            ("Valore Nominale Totale", summary.get("totale_nominale", 0)),
            ("Valore Attuale Lordo", summary.get("totale_attuale", 0)),
            ("Valore Rimborso Netto", summary.get("totale_rimborso_netto", 0)),
            ("Valore Netto a Scadenza", summary.get("totale_netto_scadenza", 0)),
        ]

        # Calculate total bollo
        totale_lordo = sum(float(r.get("valore_lordo_attuale", 0) or 0) for r in records)
        totale_bollo = sum(
            calcola_bollo(float(r.get("valore_lordo_attuale", 0) or 0), totale_lordo)
            for r in records
        )
        esente = totale_lordo < 5000
        summary_labels.append(("Bollo Annuo Totale", totale_bollo))

        for i, (label, value) in enumerate(summary_labels):
            ws_riep.write(2 + i, 0, label, workbook.add_format({"bold": True}))
            if isinstance(value, (int, float)) and i > 0:
                ws_riep.write(2 + i, 1, value, bold_money)
            else:
                ws_riep.write(2 + i, 1, value)

        if esente:
            ws_riep.write(2 + len(summary_labels), 0, "")
            ws_riep.write(2 + len(summary_labels) + 1, 0, "Esente bollo (totale < 5.000 €)",
                          workbook.add_format({"bold": True, "font_color": "#008000"}))

        # Riepilogo per tipologia table
        row = 2 + len(summary_labels) + 3
        ws_riep.write(row, 0, "Dettaglio per Tipologia",
                      workbook.add_format({"bold": True, "font_size": 12}))
        row += 1

        tip_headers = ["Tipologia", "N. Buoni", "Nominale Totale", "Lordo Attuale", "Netto Scadenza"]
        for col, h in enumerate(tip_headers):
            ws_riep.write(row, col, h, bold_fmt)

        if isinstance(riepilogo, list):
            tip_start = row + 1
            for i, tip in enumerate(riepilogo):
                r = row + 1 + i
                ws_riep.write(r, 0, tip.get("tipologia", ""))
                ws_riep.write(r, 1, tip.get("count", 0))
                ws_riep.write(r, 2, tip.get("totale_nominale", 0), money_fmt)
                ws_riep.write(r, 3, tip.get("totale_lordo_attuale", 0), money_fmt)
                ws_riep.write(r, 4, tip.get("totale_netto_scadenza", 0), money_fmt)
            tip_end = row + len(riepilogo)

            # Pie chart
            if len(riepilogo) > 0:
                pie = workbook.add_chart({"type": "pie"})
                pie.add_series({
                    "name": "Allocazione per Tipologia",
                    "categories": ["Riepilogo", tip_start, 0, tip_end, 0],
                    "values": ["Riepilogo", tip_start, 2, tip_end, 2],
                    "data_labels": {
                        "percentage": True,
                        "position": "inside_end",
                        "font": {"size": 10, "bold": True, "color": "white"},
                    },
                    "points": [
                        {"fill": {"color": "#4472C4"}},
                        {"fill": {"color": "#ED7D31"}},
                        {"fill": {"color": "#A5A5A5"}},
                        {"fill": {"color": "#FFC000"}},
                        {"fill": {"color": "#70AD47"}},
                    ],
                })
                pie.set_title({"name": "Allocazione per Tipologia (Nominale)"})
                pie.set_legend({"position": "bottom", "font": {"size": 10}})
                pie.set_size({"width": 720, "height": 500})
                ws_riep.insert_chart("G2", pie)

        ws_riep.set_column(0, 0, 30)
        ws_riep.set_column(1, 4, 18)

        # =============================================
        # SHEET 2: Lista BFP
        # =============================================
        ws_lista = workbook.add_worksheet("Lista BFP")

        list_headers = [
            "Tipologia", "Serie", "Data Sottoscr.", "Scadenza",
            "Val. Nominale", "Val. Lordo Attuale", "Ritenuta",
            "Val. Netto Attuale", "Val. Lordo Scadenza", "Ritenuta Scadenza",
            "Val. Netto Scadenza", "Bollo Annuo", "Note"
        ]
        for col, h in enumerate(list_headers):
            ws_lista.write(0, col, h, bold_fmt)

        for i, rec in enumerate(records, start=1):
            ws_lista.write(i, 0, rec.get("tipologia", ""))
            ws_lista.write(i, 1, rec.get("serie", ""))
            ws_lista.write(i, 2, str(rec.get("data_sottoscrizione", ""))[:10])
            ws_lista.write(i, 3, str(rec.get("scadenza", "") or "")[:10])
            ws_lista.write(i, 4, float(rec.get("valore_nominale", 0) or 0), money_fmt)
            ws_lista.write(i, 5, float(rec.get("valore_lordo_attuale", 0) or 0), money_fmt)
            ws_lista.write(i, 6, float(rec.get("ritenuta_fiscale", 0) or 0), money_fmt)
            ws_lista.write(i, 7, float(rec.get("valore_rimborso_netto", 0) or 0), money_fmt)
            ws_lista.write(i, 8, float(rec.get("valore_lordo_scadenza", 0) or 0), money_fmt)
            ws_lista.write(i, 9, float(rec.get("ritenuta_scadenza", 0) or 0), money_fmt)
            ws_lista.write(i, 10, float(rec.get("valore_netto_scadenza", 0) or 0), money_fmt)
            ws_lista.write(i, 11, float(rec.get("bollo_annuo", 0) or 0), money_fmt)
            ws_lista.write(i, 12, rec.get("note", "") or "")

        ws_lista.set_column(0, 0, 35)
        ws_lista.set_column(1, 1, 16)
        ws_lista.set_column(2, 3, 14)
        ws_lista.set_column(4, 11, 18)
        ws_lista.set_column(12, 12, 25)

        # =============================================
        # SHEET 3: Rendita 65-80 (if data_nascita)
        # =============================================
        if data_nascita:
            _write_rendita_sheet(workbook, records, data_nascita, totale_lordo,
                                bold_fmt, money_fmt, bold_money, header_green)

        # =============================================
        # SHEETS 4+: Piano Rimborso aggregato per serie
        # =============================================
        # Group BFPs by serie, summing nominal values
        serie_groups = {}
        for rec in records:
            serie = rec.get("serie", "")
            valore_nom = float(rec.get("valore_nominale", 0) or 0)
            if not serie or valore_nom <= 0:
                continue
            if serie not in serie_groups:
                serie_groups[serie] = {
                    "tipologia": rec.get("tipologia", ""),
                    "serie": serie,
                    "nominale_totale": 0,
                    "num_buoni": 0,
                    "data_sottoscrizione": rec.get("data_sottoscrizione", ""),
                }
            serie_groups[serie]["nominale_totale"] += valore_nom
            serie_groups[serie]["num_buoni"] += 1

        sheet_count = 0
        for serie, group in serie_groups.items():
            nominale = round(group["nominale_totale"], 2)
            result = get_piano_rimborso(serie, nominale, group["data_sottoscrizione"])
            if "error" in result:
                continue

            sheet_count += 1
            piano = result["piano"]
            riep = result["riepilogo"]

            # Sheet name: tipologia abbreviata + serie
            tipo_short = group["tipologia"][:20].replace("/", "-")
            sheet_name = f"{tipo_short} ({group['num_buoni']})"
            sheet_name = sheet_name[:31]
            existing = [ws.name for ws in workbook.worksheets()]
            if sheet_name in existing:
                sheet_name = f"{sheet_name[:28]}_{sheet_count}"

            ws = workbook.add_worksheet(sheet_name)

            # Header info
            bold = workbook.add_format({"bold": True})
            ws.write(0, 0, "Tipologia:", bold)
            ws.write(0, 1, group["tipologia"])
            ws.write(1, 0, "Serie:", bold)
            ws.write(1, 1, serie)
            ws.write(2, 0, "N. Buoni:", bold)
            ws.write(2, 1, group["num_buoni"])
            ws.write(3, 0, "Nominale Totale:", bold)
            ws.write(3, 1, nominale, money_fmt)
            ws.write(4, 0, "Val. Netto Scadenza:", bold)
            ws.write(4, 1, riep.get("valore_netto_scadenza", 0), money_fmt)
            ws.write(5, 0, "Durata:", bold)
            ws.write(5, 1, f"{riep.get('durata_massima_anni', 0)} anni")

            # Piano table
            table_row = 7
            piano_headers = [
                "Periodo", "Coeff. Lordo", "Coeff. Netto",
                "Val. Lordo", "Val. Netto", "Ritenuta",
                "Interessi Lordi", "Interessi Netti"
            ]
            for col, h in enumerate(piano_headers):
                ws.write(table_row, col, h, bold_fmt)

            for j, p in enumerate(piano):
                r = table_row + 1 + j
                ws.write(r, 0, p["periodo_label"])
                ws.write(r, 1, p["coeff_lordo"], pct_fmt)
                ws.write(r, 2, p["coeff_netto"], pct_fmt)
                ws.write(r, 3, p["valore_lordo"], money_fmt)
                ws.write(r, 4, p["valore_netto"], money_fmt)
                ws.write(r, 5, p["ritenuta"], money_fmt)
                ws.write(r, 6, p["interessi_lordi"], money_fmt)
                ws.write(r, 7, p["interessi_netti"], money_fmt)

            data_start = table_row + 1
            data_end = table_row + len(piano)

            ws.set_column(0, 0, 12)
            ws.set_column(1, 2, 14)
            ws.set_column(3, 7, 16)

            # Chart: value growth over time
            if len(piano) > 1:
                chart = workbook.add_chart({"type": "line"})
                chart.add_series({
                    "name": "Valore Lordo",
                    "categories": [sheet_name, data_start, 0, data_end, 0],
                    "values": [sheet_name, data_start, 3, data_end, 3],
                    "line": {"width": 2, "color": "#4472C4"},
                })
                chart.add_series({
                    "name": "Valore Netto",
                    "categories": [sheet_name, data_start, 0, data_end, 0],
                    "values": [sheet_name, data_start, 4, data_end, 4],
                    "line": {"width": 2, "color": "#70AD47"},
                })
                chart.add_series({
                    "name": "Interessi Netti",
                    "categories": [sheet_name, data_start, 0, data_end, 0],
                    "values": [sheet_name, data_start, 7, data_end, 7],
                    "line": {"width": 1.5, "color": "#FFC000", "dash_type": "dash"},
                })
                chart.set_title({"name": f"Piano Rimborso - {group['tipologia']} ({group['num_buoni']} buoni, {serie})"})
                chart.set_x_axis({"name": "Periodo"})
                chart.set_y_axis({"name": "EUR", "num_format": "#,##0"})
                chart.set_size({"width": 720, "height": 400})
                chart.set_legend({"position": "bottom"})

                chart_row = table_row + len(piano) + 3
                ws.insert_chart(f"A{chart_row}", chart)

        workbook.close()
        return {"success": True, "filepath": filepath}
    except Exception as e:
        return {"error": str(e)}


def _write_rendita_sheet(workbook, records, data_nascita, totale_lordo,
                         bold_fmt, money_fmt, bold_money, header_green):
    """Write the Rendita 65-80 sheet for BSF/BO65 buoni."""
    from datetime import datetime
    from services.bfp_calculator import calcola_rendita, calcola_valore_scadenza, calcola_bollo

    try:
        nascita = datetime.strptime(str(data_nascita)[:10], "%Y-%m-%d").date()
    except ValueError:
        return

    ws = workbook.add_worksheet("Rendita 65-80")

    rendita_buoni = []
    totale_mensile_lorda = 0
    totale_mensile_netta = 0
    totale_valore_65 = 0

    for bfp in records:
        serie = (bfp.get("serie") or "").upper()
        if not (serie.startswith("BO165A") or serie.startswith("SF165A")):
            continue

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

        val_65 = calcola_valore_scadenza(bfp.get("serie"), valore_nom, ds)
        valore_al_65 = val_65.get("valore_netto", valore_nom) if "error" not in val_65 else valore_nom

        totale_mensile_lorda += result["rata_mensile_lorda"]
        totale_mensile_netta += result["rata_mensile_netta"]
        totale_valore_65 += valore_al_65

        rendita_buoni.append({
            "tipologia": bfp.get("tipologia", ""),
            "serie": bfp.get("serie", ""),
            "data_sottoscrizione": str(ds)[:10],
            "valore_nominale": valore_nom,
            "eta_sottoscrizione": eta,
            "valore_al_65": valore_al_65,
            "rata_mensile_lorda": result["rata_mensile_lorda"],
            "rata_mensile_netta": result["rata_mensile_netta"],
        })

    if not rendita_buoni:
        ws.write(0, 0, "Nessun BFP BSF/BO65 trovato")
        return

    # Calculate bollo per buono
    for b in rendita_buoni:
        b["bollo_annuo"] = calcola_bollo(b["valore_al_65"], totale_valore_65)
        b["bollo_mensile"] = round(b["bollo_annuo"] / 12, 2)
        b["rata_netta_post_bollo"] = round(b["rata_mensile_netta"] - b["bollo_mensile"], 2)

    totale_bollo_annuo = round(sum(b["bollo_annuo"] for b in rendita_buoni), 2)
    totale_bollo_mensile = round(totale_bollo_annuo / 12, 2)

    # Title
    ws.write(0, 0, "Rendita 65-80 anni (BSF + BO65)",
             workbook.add_format({"bold": True, "font_size": 14}))
    ws.write(1, 0, f"Data di nascita: {str(data_nascita)[:10]}")

    # Summary
    summary_data = [
        ("Valore al 65°", totale_valore_65),
        ("Rata Mensile Netta", round(totale_mensile_netta, 2)),
        ("Rata Mensile Netta Post Bollo", round(totale_mensile_netta - totale_bollo_mensile, 2)),
        ("Rata Annua Netta", round(totale_mensile_netta * 12, 2)),
        ("Rata Annua Netta Post Bollo", round(totale_mensile_netta * 12 - totale_bollo_annuo, 2)),
        ("Totale Rendita 15 anni (Netta)", round(totale_mensile_netta * 180, 2)),
        ("Totale Rendita 15 anni (Post Bollo)", round(totale_mensile_netta * 180 - totale_bollo_annuo * 15, 2)),
        ("Bollo Annuo Totale", totale_bollo_annuo),
        ("Bollo Totale 15 anni", round(totale_bollo_annuo * 15, 2)),
    ]

    for i, (label, value) in enumerate(summary_data):
        ws.write(3 + i, 0, label, workbook.add_format({"bold": True}))
        ws.write(3 + i, 1, value, bold_money)

    # Detail table
    row = 3 + len(summary_data) + 2
    det_headers = [
        "Tipologia", "Serie", "Data Sottoscr.", "Nominale",
        "Età Sottoscr.", "Val. al 65°", "Bollo Annuo",
        "Rata Mens. Netta", "Netta Post Bollo", "Rata Mens. Lorda"
    ]
    for col, h in enumerate(det_headers):
        ws.write(row, col, h, bold_fmt)

    for i, b in enumerate(rendita_buoni):
        r = row + 1 + i
        eta_label = f"{int(b['eta_sottoscrizione'])}a"
        if b["eta_sottoscrizione"] % 1 >= 0.5:
            eta_label += " 6m"
        ws.write(r, 0, b["tipologia"])
        ws.write(r, 1, b["serie"])
        ws.write(r, 2, b["data_sottoscrizione"])
        ws.write(r, 3, b["valore_nominale"], money_fmt)
        ws.write(r, 4, eta_label)
        ws.write(r, 5, b["valore_al_65"], money_fmt)
        ws.write(r, 6, b["bollo_annuo"], money_fmt)
        ws.write(r, 7, b["rata_mensile_netta"], money_fmt)
        ws.write(r, 8, b["rata_netta_post_bollo"], money_fmt)
        ws.write(r, 9, b["rata_mensile_lorda"], money_fmt)

    ws.set_column(0, 0, 30)
    ws.set_column(1, 1, 16)
    ws.set_column(2, 2, 14)
    ws.set_column(3, 3, 14)
    ws.set_column(4, 4, 14)
    ws.set_column(5, 9, 18)
